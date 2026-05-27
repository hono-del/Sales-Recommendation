"""
KG Visualization 用 graph-path 生成（Neo4j v3 + fallback）
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from api.demo.recommend_service import recommend_for_session
from engine.recommendation_engine import RecommendationEngine

_FALLBACK_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "fallback" / "graph-path.json"
)
_MAX_NODES = 50
_CACHE_TTL_SEC = 120.0
_graph_cache: dict[str, tuple[float, dict[str, Any]]] = {}

_VALUE_LABELS = {
    "safety": "安心",
    "family": "家族時間",
    "efficiency": "効率",
    "enjoyment": "楽しさ",
    "adventure": "冒険",
}

_ARCHETYPE_BY_AXIS = {
    "safety": "安心重視型",
    "family": "Family Oriented",
    "efficiency": "効率重視型",
    "enjoyment": "楽しさ重視型",
    "adventure": "アクティブ型",
}

_LIFESTYLE_BY_ANSWER = {
    "family_center": "週末ファミリー",
    "solo": "ソロドライブ",
    "active": "アウトドア",
    "learning": "日常・通勤",
    "hobby": "趣味ドライブ",
}


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\u3040-\u30ff\u4e00-\u9fff]+", "_", text.strip())
    return s[:48] or "node"


def _load_fallback() -> dict[str, Any]:
    return json.loads(_FALLBACK_PATH.read_text(encoding="utf-8"))


def _profile_dict(session: dict[str, Any]) -> dict[str, float]:
    profile_data = session.get("profile") or {}
    inner = profile_data.get("profile") or profile_data
    return {
        "safety": float(inner.get("score_safety", 0)),
        "family": float(inner.get("score_family", 0)),
        "efficiency": float(inner.get("score_efficiency", 0)),
        "enjoyment": float(inner.get("score_enjoyment", 0)),
        "adventure": float(inner.get("score_adventure", 0)),
    }


def _why_panel(session: dict[str, Any], logic: str) -> dict[str, Any]:
    profile_data = session.get("profile") or {}
    prof = _profile_dict(session)
    values = [
        {"key": "safety", "label": "安心", "percent": int(prof.get("safety", 0))},
        {"key": "family", "label": "家族時間", "percent": int(prof.get("family", 0))},
        {"key": "efficiency", "label": "効率", "percent": int(prof.get("efficiency", 0))},
        {"key": "enjoyment", "label": "楽しさ", "percent": int(prof.get("enjoyment", 0))},
    ]
    values = sorted(values, key=lambda v: -v["percent"])[:3]
    loads = profile_data.get("detected_loads") or []
    return {
        "values": values,
        "loads": loads[:5],
        "logic": logic,
    }


def _dominant_axis(prof: dict[str, float]) -> str:
    if not prof:
        return "safety"
    return max(prof.items(), key=lambda x: x[1])[0]


def _lifestyle_label(session: dict[str, Any]) -> Optional[str]:
    for ans in session.get("answers", []):
        if ans.get("question_id") == "q2_weekend":
            return _LIFESTYLE_BY_ANSWER.get(ans.get("answer_key", ""))
    return None


def _build_logic(
    prof: dict[str, float],
    loads: list[str],
    features: list[str],
    vehicle: str,
) -> str:
    ranked = sorted(prof.items(), key=lambda x: -x[1])
    val_a = _VALUE_LABELS.get(ranked[0][0], ranked[0][0]) if ranked else "価値"
    val_b = _VALUE_LABELS.get(ranked[1][0], ranked[1][0]) if len(ranked) > 1 else ""
    load_part = loads[0] if loads else "判断負荷"
    feat_part = "、".join(features[:3]) if features else "安全・快適装備"
    head = f"{val_a} × {val_b}" if val_b else val_a
    return f"{head} × {load_part} → {feat_part} → {vehicle}"


def _resolve_vehicle(
    session: dict[str, Any],
    top_model: Optional[str],
) -> tuple[str, float, bool]:
    if top_model:
        return top_model, 0.9, False
    rec = recommend_for_session(session)
    if rec.get("recommendations"):
        top = rec["recommendations"][0]
        return top["model"], float(top.get("score", 0.85)), bool(rec.get("demo_fallback"))
    fb = _load_fallback()
    for node in fb.get("nodes", []):
        if node.get("type") == "vehicle":
            return node.get("label", "VEZEL"), float(node.get("score", 0.92)), True
    return "VEZEL", 0.92, True


def _query_neo4j_path(
    vehicle_name: str,
    mapped_needs: list[str],
) -> list[dict[str, Any]]:
    if not mapped_needs:
        return []
    engine = RecommendationEngine()
    try:
        engine.driver.verify_connectivity()
        with engine.driver.session() as session:
            result = session.run(
                """
                MATCH (v:VehicleModel {name: $vehicle_name})-[:HAS_FEATURE]->(tf:TechnicalFeature)
                      -[:REALIZES]->(cap:Capability)-[:SUPPORTS]->(n:Need)
                WHERE n.name IN $mapped_needs
                RETURN DISTINCT
                       tf.name AS feature,
                       cap.name AS capability,
                       cap.label AS cap_label,
                       n.name AS need_name,
                       n.label AS need_label
                ORDER BY tf.name
                LIMIT 50
                """,
                vehicle_name=vehicle_name,
                mapped_needs=mapped_needs,
            )
            return [dict(r) for r in result]
    finally:
        engine.close()


def _assemble_from_neo4j(
    session: dict[str, Any],
    rows: list[dict[str, Any]],
    vehicle_name: str,
    vehicle_score: float,
    demo_fallback: bool,
) -> dict[str, Any]:
    prof = _profile_dict(session)
    profile_data = session.get("profile") or {}
    loads: list[str] = list(profile_data.get("detected_loads") or [])[:3]
    axis = _dominant_axis(prof)

    nodes: list[dict[str, Any]] = [
        {
            "id": "person",
            "type": "person",
            "label": "あなた",
            "subtype": _ARCHETYPE_BY_AXIS.get(axis, "バランス型"),
        }
    ]
    edges: list[dict[str, Any]] = []

    ranked_axes = sorted(prof.items(), key=lambda x: -x[1])[:2]
    value_ids: list[str] = []
    for ax, _ in ranked_axes:
        if prof.get(ax, 0) <= 0:
            continue
        vid = f"value_{ax}"
        value_ids.append(vid)
        nodes.append(
            {
                "id": vid,
                "type": "value",
                "label": _VALUE_LABELS.get(ax, ax),
            }
        )
        edges.append({"source": "person", "target": vid, "label": "重視"})

    lifestyle = _lifestyle_label(session)
    if lifestyle:
        lid = "lifestyle_main"
        nodes.append({"id": lid, "type": "lifestyle", "label": lifestyle})
        edges.append({"source": "person", "target": lid, "label": "ライフスタイル"})

    load_ids: list[str] = []
    for i, load_text in enumerate(loads):
        lid = f"load_{i}"
        load_ids.append(lid)
        nodes.append({"id": lid, "type": "load", "label": load_text[:24]})
        if value_ids:
            edges.append(
                {
                    "source": value_ids[i % len(value_ids)],
                    "target": lid,
                    "label": "軽減したい",
                }
            )
        else:
            edges.append({"source": "person", "target": lid, "label": "負荷"})

    features: list[str] = []
    feature_ids: list[str] = []
    seen_feat: set[str] = set()
    for row in rows:
        feat_name = (row.get("feature") or "").strip()
        if not feat_name or feat_name in seen_feat:
            continue
        seen_feat.add(feat_name)
        features.append(feat_name)
        fid = f"feature_{_slug(feat_name)}"
        feature_ids.append(fid)
        nodes.append({"id": fid, "type": "feature", "label": feat_name[:32]})
        if load_ids:
            edges.append(
                {
                    "source": load_ids[len(feature_ids) % len(load_ids)],
                    "target": fid,
                    "label": "実現",
                }
            )
        if len(feature_ids) >= 3:
            break

    vid = f"vehicle_{_slug(vehicle_name)}"
    nodes.append(
        {
            "id": vid,
            "type": "vehicle",
            "label": vehicle_name,
            "score": round(vehicle_score, 3),
        }
    )
    for fid in feature_ids:
        edges.append(
            {
                "source": fid,
                "target": vid,
                "label": "搭載",
                "highlighted": True,
            }
        )

    if len(nodes) > _MAX_NODES:
        nodes = nodes[:_MAX_NODES]

    logic = _build_logic(prof, loads, features, vehicle_name)
    return {
        "demo_fallback": demo_fallback,
        "nodes": nodes,
        "edges": edges,
        "why_panel": _why_panel(session, logic),
        "source": "neo4j",
    }


def _personalize_fallback(
    session: dict[str, Any],
    vehicle_name: str,
    vehicle_score: float,
    demo_fallback: bool,
) -> dict[str, Any]:
    import copy

    data = copy.deepcopy(_load_fallback())
    prof = _profile_dict(session)
    profile_data = session.get("profile") or {}
    loads = profile_data.get("detected_loads") or data["why_panel"].get("loads", [])

    for node in data.get("nodes", []):
        if node.get("type") == "vehicle":
            node["label"] = vehicle_name
            node["score"] = round(vehicle_score, 3)

    lifestyle = _lifestyle_label(session)
    if lifestyle:
        for node in data.get("nodes", []):
            if node.get("type") == "lifestyle":
                node["label"] = lifestyle
                break

    features = [
        n["label"]
        for n in data.get("nodes", [])
        if n.get("type") == "feature"
    ]
    logic = _build_logic(prof, list(loads), features, vehicle_name)
    data["why_panel"] = _why_panel(session, logic)
    data["demo_fallback"] = demo_fallback
    data["source"] = "fallback"
    return data


def _cache_key(session_id: str, top_model: Optional[str], session: dict[str, Any]) -> str:
    profile_data = session.get("profile") or {}
    needs = ",".join(profile_data.get("mapped_needs") or [])
    return f"{session_id}:{top_model or ''}:{needs}"


def get_graph_path(
    session: dict[str, Any],
    *,
    session_id: str,
    top_model: Optional[str] = None,
) -> dict[str, Any]:
    """セッションから KG 用 nodes/edges/why_panel を返す。"""
    key = _cache_key(session_id, top_model, session)
    now = time.time()
    cached = _graph_cache.get(key)
    if cached and now - cached[0] < _CACHE_TTL_SEC:
        return cached[1]

    vehicle_name, vehicle_score, rec_fallback = _resolve_vehicle(session, top_model)
    profile_data = session.get("profile") or {}
    mapped_needs: list[str] = list(profile_data.get("mapped_needs") or [])

    result: dict[str, Any]
    try:
        rows = _query_neo4j_path(vehicle_name, mapped_needs)
        if rows:
            result = _assemble_from_neo4j(
                session,
                rows,
                vehicle_name,
                vehicle_score,
                rec_fallback,
            )
        else:
            result = _personalize_fallback(
                session, vehicle_name, vehicle_score, True
            )
    except Exception:
        result = _personalize_fallback(
            session, vehicle_name, vehicle_score, True
        )

    _graph_cache[key] = (now, result)
    return result
