"""
デモセッション向け推薦（Neo4j + fallback）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from engine.demo_profile import DemoProfileCalculator
from engine.recommendation_engine import RecommendationEngine, RecommendationRequest

_FALLBACK_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "fallback" / "recommend.json"
)

_ARCHETYPE_BY_AXIS = {
    "safety": "安心重視型",
    "family": "家族重視型",
    "efficiency": "効率重視型",
    "enjoyment": "楽しさ重視型",
    "adventure": "冒険重視型",
}

_EXCLUDE_REASONS = [
    "利用文脈との一致度が低い",
    "重視する価値軸との適合度が低い",
    "利用頻度に対してオーバースペック",
]
_MAX_EXCLUDED = 3


def _dominant_axis(profile: dict[str, float]) -> str:
    if not profile:
        return "safety"
    return max(profile.items(), key=lambda x: x[1])[0]


def _archetype_for_rank(profile: dict[str, float], rank: int) -> str:
    axis = _dominant_axis(profile)
    if rank == 0:
        return _ARCHETYPE_BY_AXIS.get(axis, "安心重視型")
    if rank == 1:
        return "バランス型"
    return _ARCHETYPE_BY_AXIS.get("enjoyment", "楽しさ重視型")


def _profile_dict_from_session(session_profile: Optional[dict]) -> dict[str, float]:
    if not session_profile:
        return {}
    inner = session_profile.get("profile") or session_profile
    return {
        "safety": float(inner.get("score_safety", 0)),
        "family": float(inner.get("score_family", 0)),
        "efficiency": float(inner.get("score_efficiency", 0)),
        "enjoyment": float(inner.get("score_enjoyment", 0)),
        "adventure": float(inner.get("score_adventure", 0)),
    }


def _load_fallback() -> dict[str, Any]:
    return json.loads(_FALLBACK_PATH.read_text(encoding="utf-8"))


def _vehicle_meta(engine: RecommendationEngine, model: str) -> dict[str, Any]:
    """車種のメタデータと訴求ポイント（Feature 上位）を取得。"""
    try:
        with engine.driver.session() as session:
            row = session.run(
                """
                MATCH (v:VehicleModel {name: $name})
                OPTIONAL MATCH (v)-[:HAS_FEATURE]->(tf:TechnicalFeature)
                RETURN v.fuel_type AS fuel_type,
                       v.seating_capacity AS seating,
                       v.price_range AS price_range,
                       collect(DISTINCT tf.name)[0..3] AS features
                """,
                name=model,
            ).single()
        if not row:
            return {}
        features = [f for f in (row.get("features") or []) if f]
        return {
            "fuel_type": row.get("fuel_type") or "",
            "seating_capacity": int(row.get("seating") or 0),
            "price_range": row.get("price_range") or "",
            "appeal_points": features[:3],
            "quick_grade": "",
        }
    except Exception:
        return {}


def _infer_usage(profile: dict[str, float], answers: list[dict]) -> str:
    if profile.get("family", 0) >= max(profile.values(), default=0) * 0.9:
        return "family_use"
    if profile.get("adventure", 0) > profile.get("efficiency", 0):
        return "outdoor"
    return "daily"


def recommend_for_session(
    session: dict[str, Any],
    *,
    family_size: int = 4,
    budget: int = 3_000_000,
) -> dict[str, Any]:
    """セッションのプロファイルから top3 推薦 + excluded を返す。"""
    profile_data = session.get("profile") or {}
    prof = _profile_dict_from_session(profile_data)
    calc = DemoProfileCalculator()
    ui_needs = profile_data.get("ui_needs") or calc.profile_to_ui_needs(prof)
    usage = _infer_usage(prof, session.get("answers", []))
    
    # Load 検出結果を取得
    detected_loads = profile_data.get("detected_loads") or []

    demo_fallback = False
    recommendations: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []

    try:
        engine = RecommendationEngine()
        try:
            engine.driver.verify_connectivity()
            req = RecommendationRequest(
                family_size=family_size,
                budget=budget,
                needs=ui_needs,
                usage=usage,
                detected_loads=detected_loads,  # Load を渡す
            )
            results = engine.recommend(req, top_k=3 + _MAX_EXCLUDED)
            for i, r in enumerate(results[:3]):
                meta = _vehicle_meta(engine, r.model)
                recommendations.append({
                    "model": r.model,
                    "score": round(r.score, 3),
                    "reason": r.reason,
                    "archetype": _archetype_for_rank(prof, i),
                    "similar_consumers": r.similar_consumers[:3],
                    "quick_grade": meta.get("quick_grade", ""),
                    "price_range": meta.get("price_range", ""),
                    "fuel_type": meta.get("fuel_type", ""),
                    "seating_capacity": meta.get("seating_capacity", 0),
                    "appeal_points": meta.get("appeal_points", []),
                    "load_boost": round(r.load_boost, 3),  # Load ブーストスコア
                    "matched_load_features": r.matched_load_features[:3],  # マッチした Load 対応機能
                })
            for r in results[3 : 3 + _MAX_EXCLUDED]:
                excluded.append({
                    "model": r.model,
                    "reason": _EXCLUDE_REASONS[len(excluded) % len(_EXCLUDE_REASONS)],
                })
        finally:
            engine.close()
    except Exception:
        demo_fallback = True

    if not recommendations:
        demo_fallback = True
        fb = _load_fallback()
        recommendations = fb.get("recommendations", [])[:3]
        excluded = fb.get("excluded", [])
        for i, rec in enumerate(recommendations):
            rec["archetype"] = _archetype_for_rank(prof, i)

    if len(excluded) < _MAX_EXCLUDED:
        fb_ex = _load_fallback().get("excluded", [])
        for item in fb_ex:
            if len(excluded) >= _MAX_EXCLUDED:
                break
            if item["model"] not in {r["model"] for r in recommendations}:
                excluded.append(item)

    return {
        "demo_fallback": demo_fallback,
        "recommendations": recommendations,
        "excluded": excluded[:_MAX_EXCLUDED],
        "ui_needs": ui_needs,
    }
