"""
KG Visualization 用 graph-path 生成（Neo4j v3 + fallback）
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from api.demo.decision_style_presentation import (
    build_style_presentation,
    enrich_reason_trace,
    _style_from_session,
)
from api.demo.explainability import (
    build_experience_items,
    build_experience_items_from_kg_needs,
    build_feature_cards,
    build_filter_funnel,
    build_reason_trace,
    build_vehicle_detail,
)
from api.demo.recommend_service import recommend_for_session, _vehicle_meta
from engine.recommendation_engine import RecommendationEngine

_FALLBACK_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "fallback" / "graph-path.json"
)
_MAX_NODES = 50
_CACHE_TTL_SEC = 120.0
_NEO4J_PATH_TIMEOUT_SEC = 4.0
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

_LOAD_TO_EXPERIENCE = {
    "駐車・狭い道への不安": "駐車を気にせず移動できる",
    "長距離移動による疲労": "長距離でも疲れにくい",
    "維持費への不安": "維持費を気にしすぎない",
    "渋滞ストレス": "渋滞でも快適に過ごせる",
    "車内の狭さ": "車内空間にゆとりがある",
    "運転操作の負担": "運転中の操作が楽になる",
}

_FEATURE_TO_REASON = {
    "Honda SENSING": "安全運転支援で負担軽減",
    "パノラミックビューモニター": "駐車ストレス軽減",
    "Google Map統合": "渋滞ストレス軽減",
    "Google Assistant": "運転中操作負荷軽減",
    "Google Play対応": "日常体験の快適性向上",
    "e:HEVシステム": "維持費バランス改善",
    "電動パーキングブレーキ": "操作負担軽減",
    "3列シート": "家族全員が快適に移動",
    "低床フロア": "乗り降りの負担軽減",
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


def _kg_needs_from_session(session: dict[str, Any]) -> list[dict[str, Any]]:
    profile_data = session.get("profile") or {}
    return list(profile_data.get("kg_needs") or [])


def _recommendations_payload(
    session: dict[str, Any], *, top_model: Optional[str] = None
) -> dict[str, Any]:
    """セッションキャッシュの推薦結果を取得。無ければ1回だけ計算。"""
    cached = session.get("cached_recommendations")
    if isinstance(cached, dict) and cached.get("payload"):
        return cached["payload"]
    if top_model:
        return {
            "demo_fallback": True,
            "recommendations": [{"model": top_model, "score": 0.85}],
            "excluded": [],
        }
    return recommend_for_session(session)


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


def _attach_style_presentation(
    session: dict[str, Any],
    thinking: dict[str, Any],
    recommendations: Optional[list[dict[str, Any]]],
) -> dict[str, Any]:
    """意思決定スタイルに応じたプレゼン層を thinking_process に付与。"""
    style = _style_from_session(session)
    if style:
        thinking["decision_style"] = style
    if not recommendations:
        return thinking
    presentation = build_style_presentation(session, thinking, recommendations)
    if presentation:
        thinking["style_presentation"] = presentation
        if thinking.get("reason_trace"):
            thinking["reason_trace"] = enrich_reason_trace(
                thinking["reason_trace"], presentation
            )
    return thinking


def _build_thinking_process(
    session: dict[str, Any],
    prof: dict[str, float],
    loads: list[str],
    features: list[str],
    vehicle_name: str,
    vehicle_score: float,
    vehicle_meta: Optional[dict[str, Any]] = None,
    recommendations: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """STEP0〜5 + Reason Trace の思考プロセスデータを生成"""

    ranked_values = sorted(prof.items(), key=lambda x: -x[1])
    values = [
        {"key": k, "label": _VALUE_LABELS.get(k, k), "percent": int(v)}
        for k, v in ranked_values[:3]
        if v > 0
    ]

    load_items = loads[:3]
    kg_needs = _kg_needs_from_session(session)
    if kg_needs:
        experiences = build_experience_items_from_kg_needs(kg_needs, prof)
    else:
        experiences = build_experience_items(prof, load_items)
    feature_items = build_feature_cards(features)
    vehicle_item = build_vehicle_detail(
        session, prof, load_items, vehicle_name, vehicle_score, vehicle_meta
    )
    filter_funnel = build_filter_funnel(session, final_count=3, fast=True)
    reason_trace = build_reason_trace(
        prof, load_items, experiences, feature_items, vehicle_item, kg_needs=kg_needs or None
    )

    thinking = {
        "filter_funnel": filter_funnel,
        "values": values,
        "loads": load_items,
        "experiences": experiences,
        "features": feature_items,
        "vehicle": vehicle_item,
        "reason_trace": reason_trace,
    }
    return _attach_style_presentation(session, thinking, recommendations)


def _resolve_vehicle(
    session: dict[str, Any],
    top_model: Optional[str],
    rec_payload: dict[str, Any],
) -> tuple[str, float, bool]:
    recs = rec_payload.get("recommendations") or []
    demo_fb = bool(rec_payload.get("demo_fallback"))
    if top_model:
        score = 0.85
        for r in recs:
            if r.get("model") == top_model:
                score = float(r.get("score", 0.85))
                break
        return top_model, score, demo_fb
    if recs:
        top = recs[0]
        return top["model"], float(top.get("score", 0.85)), demo_fb

    fb = _load_fallback()
    for node in fb.get("nodes", []):
        if node.get("type") == "vehicle":
            return node.get("label", "VEZEL"), float(node.get("score", 0.92)), True
    return "VEZEL", 0.92, True


def _query_neo4j_path(
    vehicle_name: str,
    mapped_needs: list[str],
    engine: RecommendationEngine,
) -> list[dict[str, Any]]:
    if not mapped_needs:
        return []
    deadline = time.time() + _NEO4J_PATH_TIMEOUT_SEC
    try:
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
                LIMIT 12
                """,
                vehicle_name=vehicle_name,
                mapped_needs=mapped_needs[:8],
            )
            rows = [dict(r) for r in result]
            if time.time() > deadline:
                return rows[:6]
            return rows
    except Exception:
        return []


def _assemble_from_neo4j(
    session: dict[str, Any],
    rows: list[dict[str, Any]],
    vehicle_name: str,
    vehicle_score: float,
    demo_fallback: bool,
    *,
    engine: Optional[RecommendationEngine] = None,
    recs: Optional[list[dict[str, Any]]] = None,
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

    kg_needs = _kg_needs_from_session(session)
    if kg_needs:
        experiences_data = build_experience_items_from_kg_needs(kg_needs, prof)
    else:
        experiences_data = build_experience_items(prof, loads)

    need_ids: list[str] = []
    exp_ids: list[str] = []
    need_id_by_name: dict[str, str] = {}

    if kg_needs:
        for i, need in enumerate(kg_needs[:3]):
            name = need.get("name", f"need_{i}")
            nid = f"need_{_slug(name)}"
            need_ids.append(nid)
            need_id_by_name[name] = nid
            nodes.append(
                {
                    "id": nid,
                    "type": "need",
                    "label": (need.get("label") or name)[:28],
                    "subtype": need.get("group", ""),
                }
            )
            linked = False
            src_load = need.get("source_load", "")
            if src_load:
                for j, load_text in enumerate(loads):
                    if load_text == src_load and j < len(load_ids):
                        edges.append(
                            {
                                "source": load_ids[j],
                                "target": nid,
                                "label": "ゆらぎ",
                            }
                        )
                        linked = True
                        break
            src_axis = need.get("source_axis", "")
            if not linked and src_axis:
                vid = f"value_{src_axis}"
                if any(n["id"] == vid for n in nodes):
                    edges.append(
                        {"source": vid, "target": nid, "label": "重視"}
                    )
                    linked = True
            if not linked:
                if load_ids:
                    edges.append(
                        {
                            "source": load_ids[i % len(load_ids)],
                            "target": nid,
                            "label": "欲求",
                        }
                    )
                elif value_ids:
                    edges.append(
                        {
                            "source": value_ids[i % len(value_ids)],
                            "target": nid,
                            "label": "欲求",
                        }
                    )
                else:
                    edges.append(
                        {"source": "person", "target": nid, "label": "欲求"}
                    )
    else:
        for i, exp in enumerate(experiences_data[:3]):
            eid = f"experience_{i}"
            exp_ids.append(eid)
            nodes.append(
                {
                    "id": eid,
                    "type": "experience",
                    "label": exp["label"][:28],
                }
            )
            if load_ids:
                edges.append(
                    {
                        "source": load_ids[i % len(load_ids)],
                        "target": eid,
                        "label": "必要な体験",
                    }
                )
            elif value_ids:
                edges.append(
                    {
                        "source": value_ids[i % len(value_ids)],
                        "target": eid,
                        "label": "求める体験",
                    }
                )

    features: list[str] = []
    feature_ids: list[str] = []
    benefit_ids: list[str] = []
    seen_feat: set[str] = set()
    bridge_ids = need_ids if need_ids else exp_ids
    for row in rows:
        feat_name = (row.get("feature") or "").strip()
        if not feat_name or feat_name in seen_feat:
            continue
        seen_feat.add(feat_name)
        features.append(feat_name)
        fid = f"feature_{_slug(feat_name)}"
        feature_ids.append(fid)
        nodes.append({"id": fid, "type": "feature", "label": feat_name[:32]})
        need_name = (row.get("need_name") or "").strip()
        src_id: Optional[str] = None
        if need_name and need_name in need_id_by_name:
            src_id = need_id_by_name[need_name]
        elif bridge_ids:
            src_id = bridge_ids[len(feature_ids) % len(bridge_ids)]
        if src_id:
            edges.append(
                {
                    "source": src_id,
                    "target": fid,
                    "label": "SUPPORTS" if need_ids else "実現",
                }
            )
        elif load_ids:
            edges.append(
                {
                    "source": load_ids[len(feature_ids) % len(load_ids)],
                    "target": fid,
                    "label": "実現",
                }
            )
        if len(feature_ids) >= 3:
            break

    feature_cards = build_feature_cards(features)
    for i, card in enumerate(feature_cards):
        bid = f"benefit_{i}"
        benefit_ids.append(bid)
        benefit_label = card.get("emotional_benefit", "快適さ")[:20]
        nodes.append({"id": bid, "type": "emotional_benefit", "label": benefit_label})
        if i < len(feature_ids):
            edges.append(
                {
                    "source": feature_ids[i],
                    "target": bid,
                    "label": "もたらす",
                }
            )

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
    for bid in benefit_ids:
        edges.append(
            {
                "source": bid,
                "target": vid,
                "label": "満たす",
                "highlighted": True,
            }
        )

    if len(nodes) > _MAX_NODES:
        keep_ids = {n["id"] for n in nodes[:_MAX_NODES]}
        nodes = nodes[:_MAX_NODES]
        edges = [e for e in edges if e["source"] in keep_ids and e["target"] in keep_ids]

    logic = _build_logic(prof, loads, features, vehicle_name)
    vmeta: dict[str, Any] = {}
    if engine:
        try:
            vmeta = _vehicle_meta(engine, vehicle_name)
        except Exception:
            pass

    thinking_process = _build_thinking_process(
        session,
        prof,
        loads,
        features,
        vehicle_name,
        vehicle_score,
        vmeta,
        recs or [],
    )

    return {
        "demo_fallback": demo_fallback,
        "nodes": nodes,
        "edges": edges,
        "why_panel": _why_panel(session, logic),
        "thinking_process": thinking_process,
        "source": "neo4j",
    }


def _personalize_fallback(
    session: dict[str, Any],
    vehicle_name: str,
    vehicle_score: float,
    demo_fallback: bool,
    *,
    recs: Optional[list[dict[str, Any]]] = None,
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

    thinking_process = _build_thinking_process(
        session,
        prof,
        list(loads),
        features,
        vehicle_name,
        vehicle_score,
        None,
        recs or [],
    )

    data["why_panel"] = _why_panel(session, logic)
    data["thinking_process"] = thinking_process
    data["demo_fallback"] = demo_fallback
    data["source"] = "fallback"
    return data


def _cache_key(session_id: str, top_model: Optional[str], session: dict[str, Any]) -> str:
    profile_data = session.get("profile") or {}
    needs = ",".join(profile_data.get("mapped_needs") or [])
    kg = ",".join(
        n.get("name", "") for n in (profile_data.get("kg_needs") or [])[:5]
    )
    return f"{session_id}:{top_model or ''}:{needs}:{kg}"


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

    rec_payload = _recommendations_payload(session, top_model=top_model)
    recs = list(rec_payload.get("recommendations") or [])[:3]
    vehicle_name, vehicle_score, rec_fallback = _resolve_vehicle(
        session, top_model, rec_payload
    )
    profile_data = session.get("profile") or {}
    mapped_needs: list[str] = list(profile_data.get("mapped_needs") or [])[:8]

    result: dict[str, Any]
    engine: Optional[RecommendationEngine] = None
    try:
        engine = RecommendationEngine()
        rows = _query_neo4j_path(vehicle_name, mapped_needs, engine)
        if rows:
            result = _assemble_from_neo4j(
                session,
                rows,
                vehicle_name,
                vehicle_score,
                rec_fallback,
                engine=engine,
                recs=recs,
            )
        else:
            result = _personalize_fallback(
                session,
                vehicle_name,
                vehicle_score,
                True,
                recs=recs,
            )
    except Exception:
        result = _personalize_fallback(
            session,
            vehicle_name,
            vehicle_score,
            True,
            recs=recs,
        )
    finally:
        if engine:
            engine.close()

    _graph_cache[key] = (now, result)
    return result
