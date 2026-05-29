"""
KG マスタ一覧と、セッションで特定された Need / TechnicalFeature の照合。
"""
from __future__ import annotations

from typing import Any, Optional

_NEED_CATALOG: list[dict[str, Any]] | None = None
_FEATURE_CATALOG: list[dict[str, Any]] | None = None


def _load_need_master() -> list[dict[str, Any]]:
    global _NEED_CATALOG
    if _NEED_CATALOG is not None:
        return _NEED_CATALOG
    try:
        from graph.graph_builder import NEW_NEED_MASTER

        _NEED_CATALOG = [
            {
                "name": n["name"],
                "label": n.get("label", n["name"]),
                "group": n.get("group", ""),
            }
            for n in NEW_NEED_MASTER
        ]
    except Exception:
        _NEED_CATALOG = []
    return _NEED_CATALOG


def _load_feature_catalog_from_neo4j() -> list[dict[str, Any]]:
    try:
        from engine.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        try:
            with engine.driver.session() as session:
                rows = session.run(
                    """
                    MATCH (tf:TechnicalFeature)
                    RETURN tf.name AS name, tf.category AS category
                    ORDER BY tf.category, tf.name
                    """
                )
                return [
                    {
                        "name": r["name"] or "",
                        "category": r["category"] or "general",
                    }
                    for r in rows
                    if r.get("name")
                ]
        finally:
            engine.close()
    except Exception:
        return []
    return []


def _load_feature_catalog() -> list[dict[str, Any]]:
    global _FEATURE_CATALOG
    if _FEATURE_CATALOG is not None:
        return _FEATURE_CATALOG
    neo = _load_feature_catalog_from_neo4j()
    if neo:
        _FEATURE_CATALOG = neo
        return _FEATURE_CATALOG
    _FEATURE_CATALOG = _fallback_features()
    return _FEATURE_CATALOG


def _fallback_features() -> list[dict[str, Any]]:
    """Neo4j 未接続時の代表機能リスト"""
    names = [
        ("Honda SENSING", "safety"),
        ("e:HEVシステム", "fuel_efficiency"),
        ("パノラミックビューモニター", "safety"),
        ("3列シート", "space"),
        ("低床フロア", "comfort"),
        ("電動パーキングブレーキ", "comfort"),
        ("Google Map統合", "technology"),
        ("Google Assistant", "technology"),
        ("アダプティブクルーズコントロール", "safety"),
        ("衝突軽減ブレーキ", "safety"),
        ("歩行者検知", "safety"),
        ("リアワイドビューカメラ", "safety"),
        ("静音設計ボディ", "comfort"),
        ("可変シート", "space"),
    ]
    return [{"name": n, "category": c} for n, c in names]


def _session_profile(session: dict[str, Any]) -> dict[str, Any]:
    return session.get("profile") or {}


def _selected_need_details(session: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """name -> { selected, source, weight, label, ... }"""
    profile = _session_profile(session)
    out: dict[str, dict[str, Any]] = {}
    for need in profile.get("kg_needs") or []:
        name = need.get("name")
        if name:
            out[name] = {
                "selected": True,
                "source": need.get("source", ""),
                "source_load": need.get("source_load", ""),
                "source_axis": need.get("source_axis", ""),
                "weight": need.get("weight"),
                "label": need.get("label", name),
            }
    for name in profile.get("mapped_needs") or []:
        if name not in out:
            out[name] = {"selected": True, "source": "mapped", "label": name}
    return out


def _selected_features_for_session(
    session: dict[str, Any],
    vehicle_name: Optional[str],
) -> dict[str, dict[str, Any]]:
    """feature name -> { selected, linked_needs, capability }"""
    profile = _session_profile(session)
    need_names = list(profile.get("mapped_needs") or [])[:12]
    selected: dict[str, dict[str, Any]] = {}

    if need_names:
        from engine.kg_need_resolver import query_features_for_needs

        rows = query_features_for_needs(
            need_names, vehicle_name=vehicle_name, limit=80
        )
        for row in rows:
            feat = (row.get("feature") or "").strip()
            if not feat:
                continue
            entry = selected.setdefault(
                feat,
                {
                    "selected": True,
                    "linked_needs": [],
                    "capabilities": [],
                },
            )
            nn = row.get("need_name")
            if nn and nn not in entry["linked_needs"]:
                entry["linked_needs"].append(nn)
            cap = row.get("cap_label") or row.get("capability")
            if cap and cap not in entry["capabilities"]:
                entry["capabilities"].append(cap)

    cached = session.get("cached_recommendations") or {}
    recs = (cached.get("payload") or {}).get("recommendations") or []
    for rec in recs[:1]:
        for raw in rec.get("matched_load_features") or []:
            feat = (raw.split("(")[0] if "(" in raw else raw).strip()
            if feat and feat not in selected:
                selected[feat] = {
                    "selected": True,
                    "linked_needs": need_names[:3],
                    "capabilities": [],
                }

    return selected


def build_need_catalog_view(session: dict[str, Any]) -> dict[str, Any]:
    master = _load_need_master()
    sel = _selected_need_details(session)
    items: list[dict[str, Any]] = []
    selected_count = 0
    for row in master:
        name = row["name"]
        meta = sel.get(name, {})
        is_sel = bool(meta.get("selected"))
        if is_sel:
            selected_count += 1
        items.append(
            {
                **row,
                "selected": is_sel,
                "source": meta.get("source", ""),
                "source_load": meta.get("source_load", ""),
                "source_axis": meta.get("source_axis", ""),
                "weight": meta.get("weight"),
            }
        )
    groups = sorted({i["group"] for i in items if i.get("group")})
    return {
        "kind": "needs",
        "total": len(items),
        "selected_count": selected_count,
        "groups": groups,
        "items": items,
    }


def build_feature_catalog_view(
    session: dict[str, Any],
    vehicle_name: Optional[str] = None,
) -> dict[str, Any]:
    master = _load_feature_catalog()
    sel = _selected_features_for_session(session, vehicle_name)
    items: list[dict[str, Any]] = []
    selected_count = 0
    for row in master:
        name = row["name"]
        meta = sel.get(name, {})
        is_sel = bool(meta.get("selected"))
        if is_sel:
            selected_count += 1
        items.append(
            {
                "name": name,
                "category": row.get("category", "general"),
                "selected": is_sel,
                "linked_needs": meta.get("linked_needs", []),
                "capabilities": meta.get("capabilities", []),
            }
        )
    # マスタに無いがセッションでヒットした機能を追加
    master_names = {r["name"] for r in master}
    for name, meta in sel.items():
        if name not in master_names:
            selected_count += 1
            items.append(
                {
                    "name": name,
                    "category": "session",
                    "selected": True,
                    "linked_needs": meta.get("linked_needs", []),
                    "capabilities": meta.get("capabilities", []),
                }
            )

    categories = sorted({i["category"] for i in items if i.get("category")})
    return {
        "kind": "technical_features",
        "total": len(items),
        "selected_count": selected_count,
        "vehicle_name": vehicle_name or "",
        "categories": categories,
        "items": items,
    }
