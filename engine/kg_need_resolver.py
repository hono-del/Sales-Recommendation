"""
価値観・負荷・Quick Questions 回答 → KG Need ノードへの解決。
Need → Capability → TechnicalFeature → VehicleModel は Neo4j 上の既存パスを利用。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_VALUE_LABELS = {
    "safety": "安心",
    "family": "家族時間",
    "efficiency": "効率",
    "enjoyment": "楽しさ",
    "adventure": "冒険",
}

# graph_builder マスタ（Neo4j 未接続時のフォールバック）
_NEED_LABELS_FALLBACK: dict[str, dict[str, str]] = {}


def _load_kg_links() -> dict[str, Any]:
    return json.loads((_CONFIG_DIR / "kg-need-links.json").read_text(encoding="utf-8"))


def _load_need_mapping() -> dict[str, Any]:
    return json.loads((_CONFIG_DIR / "need-mapping.json").read_text(encoding="utf-8"))


def _ensure_need_catalog() -> dict[str, dict[str, str]]:
    global _NEED_LABELS_FALLBACK
    if _NEED_LABELS_FALLBACK:
        return _NEED_LABELS_FALLBACK
    try:
        from graph.graph_builder import NEW_NEED_MASTER

        for n in NEW_NEED_MASTER:
            _NEED_LABELS_FALLBACK[n["name"]] = {
                "label": n["label"],
                "group": n.get("group", ""),
            }
    except Exception:
        pass
    return _NEED_LABELS_FALLBACK


def _fetch_need_meta_from_neo4j(names: list[str]) -> dict[str, dict[str, str]]:
    """Need ラベルはマスタを優先（プロファイル計算時の Neo4j 待ちを避ける）。"""
    if not names:
        return {}
    catalog = _ensure_need_catalog()
    out: dict[str, dict[str, str]] = {}
    for name in names:
        if name in catalog:
            out[name] = {
                "label": catalog[name].get("label", name),
                "group": catalog[name].get("group", ""),
            }
    return out


def _need_record(
    name: str,
    *,
    source: str,
    weight: float,
    source_load: str = "",
    source_axis: str = "",
    meta: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    catalog = _ensure_need_catalog()
    neo = meta or {}
    cat = catalog.get(name, {})
    return {
        "name": name,
        "label": neo.get("label") or cat.get("label") or name,
        "group": neo.get("group") or cat.get("group") or "",
        "source": source,
        "weight": round(weight, 2),
        "source_load": source_load,
        "source_axis": source_axis,
    }


def resolve_kg_needs(
    profile_scores: dict[str, float],
    loads: list[str],
    answers: Optional[list[dict[str, Any]]] = None,
    *,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    """
    価値観スコア・負荷・回答から KG Need を重み付きで解決する。

    Returns:
        [{ name, label, group, source, weight, source_load, source_axis }, ...]
    """
    links = _load_kg_links()
    mapping = _load_need_mapping()
    answer_to_needs: dict = mapping.get("answer_to_needs", {})

    scores: dict[str, float] = {}
    meta_load: dict[str, str] = {}
    meta_axis: dict[str, str] = {}

    # Quick Questions の回答 → Need（既存マッピング）
    if answers:
        sorted_ans = sorted(answers, key=lambda a: a.get("question_index", 0))
        decay = 0.92
        for i, ans in enumerate(sorted_ans):
            factor = decay ** (len(sorted_ans) - 1 - i)
            qid = ans.get("question_id", "")
            key = ans.get("answer_key", "")
            for need_name in answer_to_needs.get(qid, {}).get(key, []):
                scores[need_name] = scores.get(need_name, 0) + 12 * factor
                meta_load.setdefault(need_name, "")
                meta_axis.setdefault(need_name, "")

    # 価値観5軸 → Need
    axis_map: dict = links.get("value_axis_to_needs", {})
    if profile_scores:
        peak = max(profile_scores.values()) or 1.0
        for axis, raw in profile_scores.items():
            if raw <= 0:
                continue
            norm = raw / peak
            for need_name in axis_map.get(axis, []):
                scores[need_name] = scores.get(need_name, 0) + 18 * norm
                meta_axis[need_name] = axis

    # 負荷ラベル → Need
    load_map: dict = links.get("load_label_to_needs", {})
    for load_text in loads:
        need_names = load_map.get(load_text, [])
        if not need_names:
            for key, names in load_map.items():
                if key in load_text or load_text in key:
                    need_names = names
                    break
        for need_name in need_names:
            scores[need_name] = scores.get(need_name, 0) + 22
            meta_load[need_name] = load_text

    if not scores:
        for need_name in axis_map.get("safety", ["DrivingConfidence"])[:2]:
            scores[need_name] = 10.0
            meta_axis[need_name] = "safety"

    ranked_names = sorted(scores.keys(), key=lambda n: -scores[n])[:top_k]
    neo_meta = _fetch_need_meta_from_neo4j(ranked_names)

    out: list[dict[str, Any]] = []
    for name in ranked_names:
        src = "question"
        if meta_load.get(name):
            src = "load"
        elif meta_axis.get(name):
            src = "value"
        out.append(
            _need_record(
                name,
                source=src,
                weight=scores[name],
                source_load=meta_load.get(name, ""),
                source_axis=meta_axis.get(name, ""),
                meta=neo_meta.get(name),
            )
        )
    return out


def graph_need_names(kg_needs: list[dict[str, Any]]) -> list[str]:
    return [n["name"] for n in kg_needs if n.get("name")]


def ui_needs_from_kg_needs(
    kg_needs: list[dict[str, Any]],
    profile_scores: dict[str, float],
    mapping: Optional[dict[str, Any]] = None,
) -> list[str]:
    """推薦エンジン用 UI needs キー（既存互換）+ 上位グラフ Need 名。"""
    m = mapping or _load_need_mapping()
    profile_map: dict = m.get("profile_to_ui_needs", {})
    ui: list[str] = []
    ranked = sorted(profile_scores.items(), key=lambda x: -x[1])
    for axis, _ in ranked[:2]:
        key = profile_map.get(axis)
        if key and key not in ui:
            ui.append(key)
    for n in kg_needs[:5]:
        if n["name"] not in ui:
            ui.append(n["name"])
    return ui or ["safety", "family"]


def query_features_for_needs(
    need_names: list[str],
    vehicle_name: Optional[str] = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Need → Capability → TechnicalFeature（任意で車種で絞り込み）"""
    if not need_names:
        return []
    try:
        from engine.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        try:
            cypher = """
                MATCH (n:Need)<-[:SUPPORTS]-(cap:Capability)<-[:REALIZES]-(tf:TechnicalFeature)
                WHERE n.name IN $needs
            """
            if vehicle_name:
                cypher += """
                MATCH (v:VehicleModel {name: $vname})-[:HAS_FEATURE]->(tf)
                """
            cypher += """
                RETURN DISTINCT
                       n.name AS need_name,
                       n.label AS need_label,
                       cap.name AS capability,
                       cap.label AS cap_label,
                       tf.name AS feature
                ORDER BY need_name, feature
                LIMIT $lim
            """
            params: dict[str, Any] = {"needs": need_names, "lim": limit}
            if vehicle_name:
                params["vname"] = vehicle_name
            with engine.driver.session() as session:
                return [dict(r) for r in session.run(cypher, **params)]
        finally:
            engine.close()
    except Exception:
        return []
    return []


def query_vehicles_for_needs(
    need_names: list[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Need を最も多く満たす車種（機能経由カウント）"""
    if not need_names:
        return []
    try:
        from engine.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        try:
            with engine.driver.session() as session:
                rows = session.run(
                    """
                    MATCH (n:Need)<-[:SUPPORTS]-(cap:Capability)<-[:REALIZES]-(tf:TechnicalFeature)
                          <-[:HAS_FEATURE]-(v:VehicleModel)
                    WHERE n.name IN $needs
                    RETURN v.name AS model,
                           count(DISTINCT n) AS need_hits,
                           count(DISTINCT tf) AS feature_hits
                    ORDER BY need_hits DESC, feature_hits DESC
                    LIMIT $lim
                    """,
                    needs=need_names,
                    lim=limit,
                )
                return [dict(r) for r in rows]
        finally:
            engine.close()
    except Exception:
        return []
    return []
