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

def _generate_exclude_reason(
    vehicle_name: str,
    req: "RecommendationRequest",
    engine: "RecommendationEngine",
    top_models: list[str],
) -> str:
    """除外理由を具体的に生成"""
    try:
        with engine.driver.session() as session:
            result = session.run(
                """
                MATCH (v:VehicleModel {name: $name})
                RETURN v.seating_capacity AS seating,
                       v.price_range AS price_range,
                       v.segment AS segment,
                       v.body_type AS body_type
                """,
                name=vehicle_name,
            ).single()
            if not result:
                return "データ不足のため候補から除外"
            
            seating = result.get("seating") or 0
            price_range = result.get("price_range") or ""
            segment = result.get("segment") or ""
            body_type = result.get("body_type") or ""
            
            # 定員不足
            if req.family_size > 0 and seating > 0 and seating < req.family_size:
                return f"乗車定員{seating}人では家族{req.family_size}人の移動に不足するため"
            
            # 予算オーバー
            if price_range and req.budget_min > 0:
                import re
                nums = re.findall(r"[\d,]+", price_range.replace("万円", "0000"))
                nums = [int(n.replace(",", "")) for n in nums]
                if nums:
                    min_price = min(nums) if len(nums) >= 2 else nums[0]
                    if min_price > req.budget_max * 1.3:
                        return f"予算上限（{req.budget_max // 10000}万円）に対し価格帯が高すぎるため"
            
            # セグメント・ボディタイプの不一致
            top_segments = []
            top_body_types = []
            for top_m in top_models[:2]:
                r = session.run(
                    "MATCH (v:VehicleModel {name: $name}) RETURN v.segment AS seg, v.body_type AS bt",
                    name=top_m,
                ).single()
                if r:
                    if r.get("seg"):
                        top_segments.append(r.get("seg"))
                    if r.get("bt"):
                        top_body_types.append(r.get("bt"))
            
            if top_segments and segment and segment not in top_segments:
                if "Luxury" in segment or "Performance" in segment:
                    return "日常利用の観点から、より実用的なセグメントが適しているため"
                if "Kei" in segment and req.family_size >= 4:
                    return "家族人数に対してボディサイズが小さすぎるため"
            
            # ニーズ不一致（デフォルト）
            if "offroad" in req.needs or "adventure" in req.needs:
                if body_type in ("Sedan", "Hatchback"):
                    return "アクティブな利用シーンに対し、セダン/ハッチバックは適合度が低いため"
            
            if "family" in req.needs:
                if seating < 5:
                    return "家族利用を重視する場合、より多人数対応の車種が適しているため"
            
            return "重視する価値観・利用シーンとの適合度が、上位3台より低いため"
    
    except Exception:
        return "総合的な適合度が上位3台より低いため"
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
    
    # セッションから人数・予算を取得（入力があれば優先、なければデフォルト値）
    family_size = session.get("family_size") or family_size
    budget_min = session.get("budget_min") or budget
    budget_max = session.get("budget_max") or budget

    demo_fallback = False
    recommendations: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []

    try:
        engine = RecommendationEngine()
        try:
            req = RecommendationRequest(
                family_size=family_size,
                budget=budget,
                needs=ui_needs,
                usage=usage,
                detected_loads=detected_loads,  # Load を渡す
                budget_min=budget_min,  # 予算下限
                budget_max=budget_max,  # 予算上限
            )
            results = engine.recommend(req, top_k=3 + _MAX_EXCLUDED)
            top_score = results[0].score if results else 0
            top_meta = _vehicle_meta(engine, results[0].model) if results else {}
            
            for i, r in enumerate(results[:3]):
                meta = _vehicle_meta(engine, r.model)
                gap_vs_top = []
                if i > 0:
                    # 第1推薦との差分
                    score_diff = top_score - r.score
                    if score_diff > 0.05:
                        gap_vs_top.append(f"総合スコアが第1推薦より {int(score_diff * 100)}% 低い")
                    
                    # 価格差
                    if top_meta.get("price_range") and meta.get("price_range"):
                        try:
                            import re
                            def extract_min_price(pr: str) -> int:
                                nums = re.findall(r"[\d,]+", pr.replace("万円", "0000"))
                                if nums:
                                    return int(nums[0].replace(",", ""))
                                return 0
                            top_min = extract_min_price(top_meta["price_range"])
                            cur_min = extract_min_price(meta["price_range"])
                            if cur_min > top_min * 1.2:
                                gap_vs_top.append(f"価格が第1推薦より高め（約{(cur_min - top_min) // 10000}万円高）")
                            elif cur_min < top_min * 0.8:
                                gap_vs_top.append(f"装備・性能が第1推薦より抑えめ（約{(top_min - cur_min) // 10000}万円安）")
                        except Exception:
                            pass
                    
                    # 燃費タイプ差
                    if top_meta.get("fuel_type") == "Hybrid" and meta.get("fuel_type") != "Hybrid":
                        gap_vs_top.append("ハイブリッドではないため燃費効率がやや劣る")
                    
                    # 定員差
                    if top_meta.get("seating_capacity", 0) > meta.get("seating_capacity", 0):
                        gap_vs_top.append("定員が第1推薦より少ない")
                
                profile_data = session.get("profile") or {}
                style_label = profile_data.get("decision_style_label")
                archetype = (
                    style_label
                    if i == 0 and style_label
                    else _archetype_for_rank(prof, i)
                )
                recommendations.append({
                    "model": r.model,
                    "score": round(r.score, 3),
                    "reason": r.reason,
                    "archetype": archetype,
                    "similar_consumers": r.similar_consumers[:3],
                    "quick_grade": meta.get("quick_grade", ""),
                    "price_range": meta.get("price_range", ""),
                    "fuel_type": meta.get("fuel_type", ""),
                    "seating_capacity": meta.get("seating_capacity", 0),
                    "appeal_points": meta.get("appeal_points", []),
                    "load_boost": round(r.load_boost, 3),
                    "matched_load_features": r.matched_load_features[:3],
                    "gap_vs_top": gap_vs_top if i > 0 else [],
                })
            top_models = [r.model for r in results[:3]]
            for r in results[3 : 3 + _MAX_EXCLUDED]:
                reason = _generate_exclude_reason(r.model, req, engine, top_models)
                excluded.append({"model": r.model, "reason": reason})
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
