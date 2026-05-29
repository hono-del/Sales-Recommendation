"""
意思決定スタイルに応じた「なぜこの提案か」UI 用プレゼンテーションデータ生成。
"""
from __future__ import annotations

from typing import Any, Optional

from api.demo.explainability import _budget_display, _parse_price_range
from api.demo.social_proof_service import fetch_delegator_social_proof


def _style_from_session(session: dict[str, Any]) -> Optional[dict[str, Any]]:
    profile_data = session.get("profile") or {}
    name = profile_data.get("decision_style")
    if not name:
        return None
    return {
        "name": name,
        "label": profile_data.get("decision_style_label") or name,
        "description": profile_data.get("decision_style_description") or "",
        "confidence": profile_data.get("decision_style_confidence"),
        "secondary_label": profile_data.get("decision_style_secondary_label"),
        "is_mixed": bool(profile_data.get("decision_style_is_mixed")),
    }


def _ui_mode(style_name: str) -> str:
    return {
        "Maximizer": "comparison",
        "Satisficer": "sufficiency",
        "Authority-driven": "trusted_pick",
        "Delegator": "delegated_simple",
        "Intuitive": "experience",
        "Impulsive": "quick_pick",
    }.get(style_name, "sufficiency")


def _price_in_budget(price_range: str, budget_min: int, budget_max: int) -> tuple[bool, str]:
    if not price_range or not budget_max:
        return True, "予算目安の範囲内と推定"
    lo, hi = _parse_price_range(price_range)
    mid = (lo + hi) // 2 if hi else lo
    if budget_max and mid > budget_max * 1.1:
        return False, f"予算上限（{budget_max // 10000}万円）にやや近い"
    if budget_min and mid < budget_min * 0.7:
        return True, "予算内に余裕があり、維持費も抑えめ"
    return True, "希望予算レンジに収まりやすい"


def _build_comparison(
    session: dict[str, Any],
    thinking: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    vehicles = []
    for i, rec in enumerate(recommendations[:3]):
        rank = i + 1
        gaps = list(rec.get("gap_vs_top") or [])
        highlights: list[str] = []
        if rank == 1:
            highlights.append("総合スコアが最も高い")
            if rec.get("matched_load_features"):
                highlights.append(
                    f"検出した負荷に対応する装備: {', '.join(rec['matched_load_features'][:2])}"
                )
            verdict = "あなたの価値観・負荷・体験のバランスが最も良い一台"
        else:
            verdict = "有効な候補だが、第1位に次ぐ理由でランク"

        vehicles.append(
            {
                "rank": rank,
                "model": rec.get("model", ""),
                "score_pct": int(float(rec.get("score", 0)) * 100),
                "price_range": rec.get("price_range") or "",
                "fuel_type": rec.get("fuel_type") or "",
                "seating_capacity": rec.get("seating_capacity") or 0,
                "appeal_points": (rec.get("appeal_points") or [])[:3],
                "reason": rec.get("reason", ""),
                "highlights": highlights,
                "gaps": gaps,
                "verdict": verdict,
            }
        )

    rows: list[dict[str, Any]] = [
        {
            "label": "おすすめ度",
            "values": [f"{v['score_pct']}%" for v in vehicles],
        },
        {
            "label": "価格帯",
            "values": [v["price_range"] or "—" for v in vehicles],
        },
        {
            "label": "定員",
            "values": [
                f"{v['seating_capacity']}人" if v["seating_capacity"] else "—"
                for v in vehicles
            ],
        },
        {
            "label": "燃料",
            "values": [v["fuel_type"] or "—" for v in vehicles],
        },
    ]

    top = vehicles[0] if vehicles else {}
    why_rank1 = [
        top.get("reason") or "ニーズとの適合度が最も高い",
        f"マッチスコア {top.get('score_pct', 0)}% で3台中トップ",
    ]
    experiences = thinking.get("experiences") or []
    if experiences:
        why_rank1.append(f"重視する体験「{experiences[0].get('label', '')}」を満たしやすい")

    return {
        "ui_mode": "comparison",
        "headline": "徹底比較型のあなたへ",
        "subheadline": "3台を並べて比較し、第1位が優れる理由と2・3位の不足点を確認できます",
        "why_rank1_title": "第1位が最もおすすめな理由",
        "why_rank1_points": [p for p in why_rank1 if p],
        "vehicles": vehicles,
        "comparison_rows": rows,
    }


def _build_sufficiency(
    session: dict[str, Any],
    thinking: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    top = recommendations[0] if recommendations else {}
    budget_min = int(session.get("budget_min") or 0)
    budget_max = int(session.get("budget_max") or 0)
    price_ok, price_detail = _price_in_budget(
        top.get("price_range") or "", budget_min, budget_max
    )

    exp_items = [
        e.get("label", "") for e in (thinking.get("experiences") or [])[:3] if e.get("label")
    ]
    feat_items = [
        f.get("feature_name") or f.get("name", "")
        for f in (thinking.get("features") or [])[:3]
        if f.get("feature_name") or f.get("name")
    ]

    checklist = [
        {
            "title": "必要な体験",
            "met": len(exp_items) > 0,
            "items": exp_items or ["快適な日常移動"],
            "note": "価値観×負荷から導いた体験を満たす設計",
        },
        {
            "title": "体験を支えるポイント",
            "met": len(feat_items) > 0,
            "items": feat_items or ["安全・快適装備"],
            "note": "体験価値を具体的な装備で実現",
        },
        {
            "title": "予算・定員",
            "met": price_ok,
            "items": [
                _budget_display(session),
                f"定員 {top.get('seating_capacity', '—')}人（家族{session.get('family_size', '—')}人想定）",
            ],
            "note": price_detail,
        },
    ]

    vehicle = thinking.get("vehicle") or {}
    return {
        "ui_mode": "sufficiency",
        "headline": "十分型のあなたへ",
        "subheadline": "追加の比較は最小限でよい — 必要な条件を満たした一台を明確に提示します",
        "checklist": checklist,
        "hero_vehicle": {
            "model": top.get("model") or vehicle.get("name", ""),
            "score_pct": int(float(top.get("score", vehicle.get("score", 0))) * 100),
            "price_range": top.get("price_range") or vehicle.get("price_range", ""),
            "summary": vehicle.get("lifestyle_fit")
            or top.get("reason")
            or "日常の移動ニーズを過不足なく満たす",
            "confidence_points": vehicle.get("confidence_points")
            or [
                "維持費が想定内に収まりやすい",
                "家族利用との相性が良い",
                "日常使いで後悔しにくい",
            ],
        },
        "alternatives_note": (
            "2位・3位も基準は満たしますが、総合のバランスでは第1位が最も「十分」の水準です。"
            if len(recommendations) > 1
            else ""
        ),
    }


def _build_trusted_pick(
    session: dict[str, Any],
    thinking: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    top = recommendations[0] if recommendations else {}
    similar = top.get("similar_consumers") or []
    return {
        "ui_mode": "trusted_pick",
        "headline": "権威依存型のあなたへ",
        "subheadline": "専門的評価と類似購入者の選択実績を重視した提案です",
        "hero_vehicle": {
            "model": top.get("model", ""),
            "score_pct": int(float(top.get("score", 0)) * 100),
            "proof_points": [
                f"類似の家族構成・価値観の購入者 {len(similar)}名が選択",
                "ニーズ適合度 " + str(int(float(top.get("score", 0)) * 100)) + "%",
                "安全・快適装備の評価が高いモデル",
            ],
            "reason": top.get("reason", ""),
        },
        "also_considered": [
            {"model": r.get("model"), "note": r.get("reason", "")[:60]}
            for r in recommendations[1:3]
        ],
    }


def _build_delegated_simple(
    session: dict[str, Any],
    thinking: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    top = recommendations[0] if recommendations else {}
    model = top.get("model", "")
    social = fetch_delegator_social_proof(session, model) if model else {}

    similar = top.get("similar_consumers") or []
    trust_note = (
        f"あなたに近い属性の購入者 {len(similar)}名が同じ車種を選んでいます"
        if similar
        else "多くの購入者の体験談と専門家の評価をもとに、1台に絞りました"
    )

    return {
        "ui_mode": "delegated_simple",
        "headline": "委任型のあなたへ",
        "subheadline": "比較表は最小限に。他の購入者のレビューと専門家・有識者の声を中心にご提案します",
        "hero_vehicle": {
            "model": model,
            "one_liner": "購入者・専門家の声を踏まえ、この1台で進めて問題ない水準です",
            "reason": top.get("reason", ""),
            "trust_note": trust_note,
        },
        "buyer_reviews": social.get("buyer_reviews") or [],
        "expert_voices": social.get("expert_voices") or [],
        "review_count_label": social.get("review_count_label", ""),
        "expert_count_label": social.get("expert_count_label", ""),
        "optional_others": [r.get("model") for r in recommendations[1:3]],
    }


def _build_experience(
    thinking: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    top = recommendations[0] if recommendations else {}
    features = thinking.get("features") or []
    scenes = [f.get("headline", "") for f in features[:2] if f.get("headline")]
    return {
        "ui_mode": "experience",
        "headline": "直感型のあなたへ",
        "subheadline": "スペック表より、乗ったときの体験・情景で選べる一台です",
        "scenes": scenes,
        "hero_vehicle": {
            "model": top.get("model", ""),
            "feeling": "試乗や日常使いで「しっくりくる」バランス",
            "reason": top.get("reason", ""),
        },
    }


def _build_quick_pick(
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    top = recommendations[0] if recommendations else {}
    return {
        "ui_mode": "quick_pick",
        "headline": "衝動型のあなたへ",
        "subheadline": "要点だけ — 迷わず決められる1台です",
        "hero_vehicle": {
            "model": top.get("model", ""),
            "score_pct": int(float(top.get("score", 0)) * 100),
            "price_range": top.get("price_range", ""),
            "quick_reason": (top.get("reason") or "").split("、")[0],
        },
    }


def build_style_presentation(
    session: dict[str, Any],
    thinking_process: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    style = _style_from_session(session)
    if not style or not recommendations:
        return None

    name = style["name"]
    mode = _ui_mode(name)

    if mode == "comparison":
        body = _build_comparison(session, thinking_process, recommendations)
    elif mode == "sufficiency":
        body = _build_sufficiency(session, thinking_process, recommendations)
    elif mode == "trusted_pick":
        body = _build_trusted_pick(session, thinking_process, recommendations)
    elif mode == "delegated_simple":
        body = _build_delegated_simple(session, thinking_process, recommendations)
    elif mode == "experience":
        body = _build_experience(thinking_process, recommendations)
    else:
        body = _build_quick_pick(recommendations)

    return {
        **body,
        "style_name": name,
        "style_label": style["label"],
        "style_description": style["description"],
        "style_confidence": style.get("confidence"),
        "style_secondary_label": style.get("secondary_label"),
        "is_mixed": style.get("is_mixed", False),
    }


def enrich_reason_trace(
    reason_trace: dict[str, Any],
    style_presentation: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if not style_presentation:
        return reason_trace
    steps = list(reason_trace.get("steps") or [])
    label = style_presentation.get("style_label", "")
    mode = style_presentation.get("ui_mode", "")
    mode_note = {
        "comparison": "3台比較で最適解を提示",
        "sufficiency": "必要十分な1台を明確化",
        "trusted_pick": "実績・評価を重視",
        "delegated_simple": "購入者レビュー・専門家の声で1台に集約",
        "experience": "体験・情景で納得",
        "quick_pick": "要点のみで即決支援",
    }.get(mode, "")
    insert = {"step": f"あなたの決め方（{label}）", "summary": mode_note}
    if steps and steps[0].get("step") == "候補の絞り込み":
        steps.insert(1, insert)
    else:
        steps.insert(0, insert)
    return {"steps": steps}
