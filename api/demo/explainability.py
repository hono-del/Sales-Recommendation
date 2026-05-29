"""
デモ「なぜこの提案か」— 説明可能性・感情負荷軽減用データ生成
"""
from __future__ import annotations

import re
from typing import Any, Optional

from engine.demo_profile import DemoProfileCalculator
from engine.recommendation_engine import RecommendationEngine, RecommendationRequest

_VALUE_LABELS = {
    "safety": "安心",
    "family": "家族時間",
    "efficiency": "効率",
    "enjoyment": "楽しさ",
    "adventure": "冒険",
}

_LIFESTYLE_BY_ANSWER = {
    "family_center": "週末ファミリー",
    "solo": "ソロドライブ",
    "active": "アウトドア",
    "learning": "日常・通勤",
    "hobby": "趣味ドライブ",
}

# 負荷 × 価値軸 → 体験ラベル
_LOAD_VALUE_EXPERIENCE: dict[str, dict[str, str]] = {
    "長距離移動による疲労": {
        "efficiency": "長距離でも疲れにくい移動",
        "family": "家族時間を損なわない移動",
        "enjoyment": "移動そのものを楽しめる",
        "safety": "安心して長距離を走れる",
        "adventure": "遠出しても体力を残せる",
    },
    "維持費への不安": {
        "efficiency": "維持費を気にしすぎない",
        "family": "家計に優しい日常使い",
        "safety": "予算内で安心の維持",
        "enjoyment": "コストを気にせず楽しめる",
        "adventure": "遊びの予算も確保できる",
    },
    "渋滞ストレス": {
        "efficiency": "渋滞でも時間を有効活用",
        "family": "渋滞中も家族との会話に余裕",
        "enjoyment": "渋滞でも気分が上がる",
        "safety": "渋滞でも安心の運転支援",
        "adventure": "渋滞を気にしない移動",
    },
    "駐車・狭い道への不安": {
        "efficiency": "駐車を素早く終えられる",
        "family": "家族同乗でも駐車が楽",
        "safety": "狭い道でも安心して運転",
        "enjoyment": "駐車のストレスなく出かけられる",
        "adventure": "狭い場所でも自在に動ける",
    },
    "車内の狭さ": {
        "family": "家族全員がゆったり過ごせる",
        "efficiency": "荷物も人も効率よく積める",
        "enjoyment": "車内でくつろげる空間",
        "safety": "安全で広いキャビン",
        "adventure": "ギアも余裕で積める",
    },
    "運転操作の負担": {
        "efficiency": "操作が少なく楽な運転",
        "family": "運転に集中しすぎない",
        "enjoyment": "運転そのものが軽く感じられる",
        "safety": "支援機能で負担軽減",
        "adventure": "操作に気を取られない",
    },
    "家族同乗時の不満リスク": {
        "family": "家族全員が快適に移動できる",
        "safety": "家族を安心して乗せられる",
        "efficiency": "同乗者の不満を減らす",
        "enjoyment": "車内が盛り上がる空間",
        "adventure": "みんなで出かけたくなる",
    },
    "情報量増加による判断負荷": {
        "efficiency": "迷わない移動",
        "family": "家族の予定に合わせやすい",
        "safety": "判断に迷わない安心",
        "enjoyment": "選びすぎない快適さ",
        "adventure": "行き先を気軽に変えられる",
    },
}

_DEFAULT_EXPERIENCE = {
    "efficiency": "快適で効率的な移動",
    "family": "家族時間を大切にできる移動",
    "enjoyment": "移動そのものを楽しめる",
    "safety": "安心して毎日使える移動",
    "adventure": "アクティブに動ける移動",
}

# 機能 → 体験カード（情景訴求）
_FEATURE_CARDS: dict[str, dict[str, str]] = {
    "Honda SENSING": {
        "headline": "長距離でも、神経を張り続けなくていい",
        "body": "高速道路や渋滞時の運転負荷を軽減。家族との会話や景色に、少し余裕を持てます。",
        "emotional_benefit": "余裕",
        "icon": "shield",
    },
    "Honda SENSING セーフティ・サポートシステム": {
        "headline": "長距離でも、神経を張り続けなくていい",
        "body": "高速道路や渋滞時の運転負荷を軽減。家族との会話や景色に、少し余裕を持てます。",
        "emotional_benefit": "余裕",
        "icon": "shield",
    },
    "e:HEVシステム": {
        "headline": "維持費を気にしすぎない安心感",
        "body": "燃費効率が高く、日常利用時のコスト不安を軽減。家計と相談しやすくなります。",
        "emotional_benefit": "安心感",
        "icon": "leaf",
    },
    "2モーターハイブリッドシステム e:HEV": {
        "headline": "維持費を気にしすぎない安心感",
        "body": "燃費効率が高く、日常利用時のコスト不安を軽減。家計と相談しやすくなります。",
        "emotional_benefit": "安心感",
        "icon": "leaf",
    },
    "Honda CONNECT": {
        "headline": "“迷わない”移動へ",
        "body": "渋滞回避や音声操作で、移動中の小さなストレスを減らします。",
        "emotional_benefit": "迷わない安心",
        "icon": "connect",
    },
    "Honda CONNECT (コネクテッド技術)": {
        "headline": "“迷わない”移動へ",
        "body": "渋滞回避や音声操作で、移動中の小さなストレスを減らします。",
        "emotional_benefit": "迷わない安心",
        "icon": "connect",
    },
    "Google Map統合": {
        "headline": "“迷わない”移動へ",
        "body": "ルート案内と渋滞情報で、到着前の不安を減らします。",
        "emotional_benefit": "迷わない安心",
        "icon": "map",
    },
    "Google マップ統合": {
        "headline": "“迷わない”移動へ",
        "body": "ルート案内と渋滞情報で、到着前の不安を減らします。",
        "emotional_benefit": "迷わない安心",
        "icon": "map",
    },
    "Google Assistant": {
        "headline": "運転中、視線を外さなくていい",
        "body": "音声操作でナビや音楽を切り替え。操作のたびに神経を使わなくて済みます。",
        "emotional_benefit": "操作負担の軽減",
        "icon": "voice",
    },
    "Google アシスタント": {
        "headline": "運転中、視線を外さなくていい",
        "body": "音声操作でナビや音楽を切り替え。操作のたびに神経を使わなくて済みます。",
        "emotional_benefit": "操作負担の軽減",
        "icon": "voice",
    },
    "Google Play対応": {
        "headline": "車内が、いつもの快適空間に",
        "body": "お気に入りのアプリで、移動時間を自分らしく過ごせます。",
        "emotional_benefit": "快適さ",
        "icon": "app",
    },
    "パノラミックビューモニター": {
        "headline": "駐車で、周りを気にしすぎない",
        "body": "周囲を俯瞰できるので、狭い場所でも落ち着いて駐車できます。",
        "emotional_benefit": "駐車の安心",
        "icon": "camera",
    },
    "3列シート": {
        "headline": "家族全員、ゆったり乗れる",
        "body": "週末のお出かけでも、誰かが我慢しなくて済む空間です。",
        "emotional_benefit": "家族の満足",
        "icon": "seat",
    },
    "静粛性": {
        "headline": "移動中、会話が途切れにくい",
        "body": "静かな車内で、家族との時間や音楽を楽しめます。",
        "emotional_benefit": "静かな余裕",
        "icon": "quiet",
    },
    "低床フロア": {
        "headline": "乗り降りが、日常の負担にならない",
        "body": "足元の負担が少なく、毎日の移動が楽になります。",
        "emotional_benefit": "身体の負担軽減",
        "icon": "entry",
    },
    "電動パーキングブレーキ": {
        "headline": "細かい操作を、任せられる",
        "body": "駐車時の操作が減り、運転の最後まで楽になります。",
        "emotional_benefit": "操作の楽さ",
        "icon": "brake",
    },
}

_BUDGET_LABELS = {
    "~200": "〜200万円",
    "200-300": "200〜300万円",
    "300-400": "300〜400万円",
    "400-500": "400〜500万円",
    "500~": "500万円以上",
}


def _dominant_axis(prof: dict[str, float]) -> str:
    if not prof:
        return "safety"
    return max(prof.items(), key=lambda x: x[1])[0]


def _second_axis(prof: dict[str, float]) -> str:
    ranked = sorted(prof.items(), key=lambda x: -x[1])
    return ranked[1][0] if len(ranked) > 1 else ranked[0][0]


def _lifestyle_label(session: dict[str, Any]) -> Optional[str]:
    for ans in session.get("answers", []):
        if ans.get("question_id") == "q2_weekend":
            return _LIFESTYLE_BY_ANSWER.get(ans.get("answer_key", ""))
    return None


def _budget_display(session: dict[str, Any]) -> str:
    br = session.get("budget_range") or ""
    if br in _BUDGET_LABELS:
        return _BUDGET_LABELS[br]
    bmin = session.get("budget_min")
    bmax = session.get("budget_max")
    if bmin and bmax:
        return f"{int(bmin) // 10000}〜{int(bmax) // 10000}万円"
    return "未指定"


def _match_load_key(load_text: str) -> str:
    for key in _LOAD_VALUE_EXPERIENCE:
        if key in load_text or load_text in key:
            return key
    return load_text


def build_experience_items_from_kg_needs(
    kg_needs: list[dict[str, Any]],
    prof: Optional[dict[str, float]] = None,
) -> list[dict[str, Any]]:
    """KG Need ノードを「必要な体験」として提示（価値観・負荷と Need を明示）。"""
    prof = prof or {}
    val_labels = _VALUE_LABELS
    items: list[dict[str, Any]] = []

    for need in kg_needs[:3]:
        name = need.get("name", "")
        label = need.get("label", name)
        group = need.get("group", "")
        source = need.get("source", "")
        source_load = need.get("source_load", "")
        source_axis = need.get("source_axis", "")
        axis_label = val_labels.get(source_axis, source_axis) if source_axis else ""

        parts: list[str] = []
        if source_axis and axis_label:
            parts.append(f"あなたの価値観「{axis_label}」")
        if source_load:
            parts.append(f"検出された負荷「{source_load}」")
        if source == "question":
            parts.append("Quick Questions の回答")
        intro = "と、".join(parts) if parts else "あなたのプロファイル"

        why_body = (
            f"{intro}から、ナレッジグラフ上の生活欲求\n"
            f"「{label}」（{name}）が重要と判断されました。\n\n"
            f"この欲求を満たす機能・車種をKG上でたどっています。"
        )
        if group:
            why_body += f"\n（カテゴリ: {group}）"

        items.append(
            {
                "label": label,
                "need_name": name,
                "need_group": group,
                "load_source": source_load,
                "value_axes": [source_axis] if source_axis else [],
                "why_title": "なぜこの体験なのか？",
                "why_body": why_body,
            }
        )

    if not items and prof:
        return build_experience_items(prof, [])
    return items


def build_experience_items(
    prof: dict[str, float],
    loads: list[str],
) -> list[dict[str, Any]]:
    """価値観 × 負荷 → 必要な体験（理由付き）— レガシールール（kg_needs 未使用時）"""
    primary = _dominant_axis(prof)
    secondary = _second_axis(prof)
    val_primary = _VALUE_LABELS.get(primary, primary)
    val_secondary = _VALUE_LABELS.get(secondary, secondary)

    items: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    # 負荷から導かれる体験
    for load in loads[:2]:
        load_key = _match_load_key(load)
        exp_map = _LOAD_VALUE_EXPERIENCE.get(load_key, {})
        label = exp_map.get(primary) or exp_map.get(secondary) or _DEFAULT_EXPERIENCE.get(
            primary, "快適な移動体験"
        )
        if label in seen_labels:
            continue
        seen_labels.add(label)

        why_body = _experience_why_body(load, load_key, primary, val_primary, val_secondary)
        items.append(
            {
                "label": label,
                "load_source": load,
                "value_axes": [primary, secondary],
                "why_title": "なぜこの体験なのか？",
                "why_body": why_body,
            }
        )

    # 価値観から直接導かれる体験（楽しさ・冒険など）
    ranked_values = sorted(prof.items(), key=lambda x: -x[1])
    for axis, score in ranked_values[:3]:
        if score < 40:
            continue
        if axis in ("enjoyment", "adventure") and len(items) < 3:
            val_label = _VALUE_LABELS.get(axis, axis)
            exp_label = _DEFAULT_EXPERIENCE.get(axis, "快適な移動体験")
            if exp_label in seen_labels:
                continue
            seen_labels.add(exp_label)
            
            if axis == "enjoyment":
                why_body = (
                    f"あなたは「{val_label}」を重視しています。\n"
                    f"単なる移動手段ではなく、運転や移動そのものを楽しめる体験が必要です。"
                )
            elif axis == "adventure":
                why_body = (
                    f"あなたは「{val_label}」を求めています。\n"
                    f"遠出やアウトドアなど、行動範囲を広げられる体験が必要です。"
                )
            else:
                why_body = f"あなたは「{val_label}」を大切にしているため、この体験が重要です。"
            
            items.append(
                {
                    "label": exp_label,
                    "load_source": "",
                    "value_axes": [axis],
                    "why_title": "なぜこの体験なのか？",
                    "why_body": why_body,
                }
            )

    if not items:
        label = _DEFAULT_EXPERIENCE.get(primary, "快適な移動体験")
        items.append(
            {
                "label": label,
                "load_source": "",
                "value_axes": [primary],
                "why_title": "なぜこの体験なのか？",
                "why_body": (
                    f"あなたは「{val_primary}」を特に重視しているため、"
                    f"日常の移動がその価値を損なわない体験が必要です。"
                ),
            }
        )
    return items[:3]


def _experience_why_body(
    load: str,
    load_key: str,
    primary: str,
    val_primary: str,
    val_secondary: str,
) -> str:
    if "疲労" in load or load_key == "長距離移動による疲労":
        if primary == "efficiency":
            return (
                f"あなたは「{val_primary}」を重視しており、\n"
                f"長距離移動の疲労を負担に感じています。\n\n"
                f"そのため、移動そのものをラクに感じられる体験が必要です。"
            )
        if primary == "family":
            return (
                f"あなたは「{val_primary}」を大切にしているため、\n"
                f"移動で疲れてしまうと、本来楽しみたい時間が損なわれます。\n\n"
                f"そのため、疲れにくさが重要になります。"
            )
        if primary == "enjoyment":
            return (
                f"あなたは「{val_primary}」を求めているため、\n"
                f"疲れた状態では運転そのものを楽しめません。\n\n"
                f"そのため、移動を楽しめる体験が必要です。"
            )
    if "維持費" in load:
        return (
            f"あなたは「{val_primary}」を重視し、\n"
            f"維持費への不安を抱えています。\n\n"
            f"そのため、コストを気にしすぎず日常使いできる体験が必要です。"
        )
    if "家族" in load or "同乗" in load:
        return (
            f"あなたは「{val_primary}」と「{val_secondary}」を大切にしており、\n"
            f"同乗者の不満やストレスを避けたいと考えています。\n\n"
            f"そのため、全員が快適に過ごせる体験が必要です。"
        )
    return (
        f"あなたは「{val_primary}」を重視し、\n"
        f"「{load}」という負荷を感じています。\n\n"
        f"そのため、この負荷を軽く感じられる体験が必要です。"
    )


def build_feature_cards(feature_names: list[str]) -> list[dict[str, Any]]:
    """機能カード生成（機能名も含める）"""
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in feature_names:
        if not name or name in seen:
            continue
        seen.add(name)
        catalog = _FEATURE_CARDS.get(name)
        if not catalog:
            # 部分一致
            for key, val in _FEATURE_CARDS.items():
                if key in name or name in key:
                    catalog = val
                    break
        if catalog:
            cards.append({"name": name, "feature_name": name, **catalog})
        else:
            cards.append(
                {
                    "name": name,
                    "feature_name": name,
                    "headline": "日常の移動が、少し楽になる",
                    "body": f"この装備が、あなたの重視する体験を支えます。",
                    "emotional_benefit": "快適さ",
                    "icon": "feature",
                }
            )
        if len(cards) >= 3:
            break
    return cards


def build_vehicle_detail(
    session: dict[str, Any],
    prof: dict[str, float],
    loads: list[str],
    vehicle_name: str,
    vehicle_score: float,
    vehicle_meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    meta = vehicle_meta or {}
    primary = _dominant_axis(prof)
    val_primary = _VALUE_LABELS.get(primary, primary)
    val_secondary = _VALUE_LABELS.get(_second_axis(prof), "")
    load_part = "、".join(loads[:2]) if loads else "日常の負荷"
    lifestyle = _lifestyle_label(session) or "日常利用"

    val_text = f"{val_primary} × {val_secondary}" if val_secondary else val_primary
    reason = f"{val_text}と{load_part}との相性が高いため"
    lifestyle_fit = f"{lifestyle}に適したボディサイズと使い勝手"

    confidence: list[str] = []
    if primary in ("efficiency", "family"):
        confidence.append("維持費が想定内に収まりやすい")
    if primary == "family" or session.get("family_size", 0) >= 4:
        confidence.append("家族利用との相性が良い")
    confidence.append("日常使いで後悔しにくい")
    if meta.get("fuel_type") and "Hybrid" in str(meta.get("fuel_type", "")):
        confidence.append("燃費と走行のバランスが取りやすい")

    grade = meta.get("quick_grade") or meta.get("grade") or ""
    display_name = f"{vehicle_name} {grade}".strip() if grade else vehicle_name

    return {
        "name": vehicle_name,
        "display_name": display_name,
        "score": round(vehicle_score, 3),
        "reason": reason,
        "lifestyle_fit": lifestyle_fit,
        "seating_capacity": meta.get("seating_capacity") or session.get("family_size") or 5,
        "price_range": meta.get("price_range") or "",
        "fuel_type": meta.get("fuel_type") or "",
        "confidence_points": confidence[:3],
    }


def build_reason_trace(
    prof: dict[str, float],
    loads: list[str],
    experiences: list[dict[str, Any]],
    features: list[dict[str, Any]],
    vehicle: dict[str, Any],
    kg_needs: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """提案根拠の追跡（Reason Trace）"""
    steps = []
    ranked = sorted(prof.items(), key=lambda x: -x[1])[:3]
    steps.append(
        {
            "step": "価値観の抽出",
            "summary": "、".join(_VALUE_LABELS.get(k, k) for k, _ in ranked),
        }
    )
    if loads:
        steps.append({"step": "負荷の検出", "summary": "、".join(loads[:3])})
    if kg_needs:
        steps.append(
            {
                "step": "KG生活欲求への結合",
                "summary": "、".join(n.get("label", n.get("name", "")) for n in kg_needs[:3]),
            }
        )
    if experiences:
        steps.append(
            {
                "step": "必要な体験の導出",
                "summary": " × ".join(
                    [e["label"] for e in experiences[:2]]
                ),
            }
        )
    if features:
        steps.append(
            {
                "step": "体験を支える機能",
                "summary": "、".join(f.get("name", "") for f in features[:3]),
            }
        )
    steps.append(
        {
            "step": "最終提案",
            "summary": f"{vehicle.get('name', '')}（マッチ {int(vehicle.get('score', 0) * 100)}%）",
        }
    )
    return {"steps": steps}


def _parse_price_range(price_range: str) -> tuple[int, int]:
    if not price_range:
        return 0, 99_999_999
    nums = re.findall(r"[\d,]+", price_range.replace("万円", "0000"))
    nums = [int(n.replace(",", "")) for n in nums]
    if len(nums) >= 2:
        return min(nums), max(nums)
    if len(nums) == 1:
        return 0, nums[0]
    return 0, 99_999_999


def _build_filter_funnel_fast(
    session: dict[str, Any], final_count: int = 3
) -> dict[str, Any]:
    """Neo4j なしの軽量ファネル（graph-path 用）。"""
    family_size = int(session.get("family_size") or 4)
    budget_min = int(session.get("budget_min") or 0)
    budget_max = int(session.get("budget_max") or 0)
    lifestyle = _lifestyle_label(session) or "日常利用"
    input_conditions = {
        "family_size": family_size,
        "budget_label": _budget_display(session),
        "lifestyle": lifestyle,
        "budget_min": budget_min,
        "budget_max": budget_max,
    }
    stages = [
        {"label": "初期候補", "count": 32, "filter_key": "initial"},
        {
            "label": f"乗員人数：{family_size}人以上",
            "count": 18,
            "filter_key": "seating",
            "excluded_reason": f"{family_size}人以上乗車が必要 → コンパクト2列車を除外",
        },
        {
            "label": f"予算：{_budget_display(session)}",
            "count": 8,
            "filter_key": "budget",
            "excluded_reason": "予算帯に合わない上位SUVを除外",
        },
        {
            "label": "利用シーン・価値観との一致",
            "count": final_count,
            "filter_key": "scene",
            "excluded_reason": "重視する価値軸との適合度が低い車種を除外",
        },
    ]
    exclusion_notes = [s.get("excluded_reason", "") for s in stages if s.get("excluded_reason")]
    return {
        "input": input_conditions,
        "stages": stages,
        "exclusion_notes": [n for n in exclusion_notes if n],
    }


def build_filter_funnel(
    session: dict[str, Any], final_count: int = 3, *, fast: bool = False
) -> dict[str, Any]:
    """STEP0: 候補絞り込みファネル"""
    if fast:
        return _build_filter_funnel_fast(session, final_count)
    family_size = int(session.get("family_size") or 4)
    budget_min = int(session.get("budget_min") or 0)
    budget_max = int(session.get("budget_max") or 0)
    lifestyle = _lifestyle_label(session) or "日常利用"

    profile_data = session.get("profile") or {}
    calc = DemoProfileCalculator()
    prof = profile_data.get("profile") or profile_data
    if isinstance(prof, dict) and "score_safety" in prof:
        ui_needs = profile_data.get("ui_needs") or calc.profile_to_ui_needs(
            {
                "safety": float(prof.get("score_safety", 0)),
                "family": float(prof.get("score_family", 0)),
                "efficiency": float(prof.get("score_efficiency", 0)),
                "enjoyment": float(prof.get("score_enjoyment", 0)),
                "adventure": float(prof.get("score_adventure", 0)),
            }
        )
    else:
        ui_needs = profile_data.get("ui_needs") or ["safety", "family"]

    input_conditions = {
        "family_size": family_size,
        "budget_label": _budget_display(session),
        "lifestyle": lifestyle,
        "budget_min": budget_min,
        "budget_max": budget_max,
    }

    stages: list[dict[str, Any]] = []
    exclusion_notes: list[str] = []

    try:
        engine = RecommendationEngine()
        try:
            vehicles = engine._get_all_vehicles()  # noqa: SLF001
            total = len(vehicles)
            stages.append({"label": "初期候補", "count": total, "filter_key": "initial"})

            after_seating = [
                v
                for v in vehicles
                if not v.get("seating")
                or int(v.get("seating") or 0) >= family_size
            ]
            seating_excluded = total - len(after_seating)
            if seating_excluded > 0:
                exclusion_notes.append(
                    f"{family_size}人以上乗車が必要 → 定員不足のコンパクト車など {seating_excluded} 車種を除外"
                )
            stages.append(
                {
                    "label": f"乗員人数：{family_size}人以上",
                    "count": len(after_seating),
                    "filter_key": "seating",
                    "excluded_reason": exclusion_notes[-1] if exclusion_notes else "",
                }
            )

            bmin = budget_min if budget_min > 0 else 0
            bmax = budget_max if budget_max > 0 else 99_999_999
            after_budget = []
            budget_excluded = 0
            for v in after_seating:
                vmin, vmax = _parse_price_range(v.get("price_range") or "")
                if bmin > 0 and vmax > 0 and vmin > bmax * 1.2:
                    budget_excluded += 1
                    continue
                if bmin > 0 and vmax > 0 and vmax < bmin * 0.8:
                    budget_excluded += 1
                    continue
                after_budget.append(v)
            if budget_excluded > 0:
                bl = _budget_display(session)
                exclusion_notes.append(
                    f"予算{bl} → 価格帯が合わない上位モデルなど {budget_excluded} 車種を除外"
                )
            stages.append(
                {
                    "label": f"予算：{_budget_display(session)}",
                    "count": len(after_budget),
                    "filter_key": "budget",
                    "excluded_reason": exclusion_notes[-1] if len(exclusion_notes) > len(stages) - 1 else "",
                }
            )

            # 利用シーン（ニーズマッチでスコアリング後、上位のみ残る想定）
            req = RecommendationRequest(
                family_size=family_size,
                budget=bmin or 3_000_000,
                needs=ui_needs,
                budget_min=bmin,
                budget_max=bmax,
                detected_loads=profile_data.get("detected_loads") or [],
            )
            scored = engine.recommend(req, top_k=max(final_count, 3))
            scene_count = len(scored) if scored else min(len(after_budget), final_count)
            scene_excluded = max(0, len(after_budget) - scene_count)
            if scene_excluded > 0:
                exclusion_notes.append(
                    f"利用シーン・重視価値との一致度 → 適合度の低い {scene_excluded} 車種を除外"
                )
            stages.append(
                {
                    "label": "利用シーン・価値観との一致",
                    "count": scene_count,
                    "filter_key": "scene",
                    "excluded_reason": exclusion_notes[-1] if exclusion_notes else "",
                }
            )
        finally:
            engine.close()
    except Exception:
        stages = [
            {"label": "初期候補", "count": 32, "filter_key": "initial"},
            {
                "label": f"乗員人数：{family_size}人以上",
                "count": 18,
                "filter_key": "seating",
                "excluded_reason": f"{family_size}人以上乗車が必要 → コンパクト2列車を除外",
            },
            {
                "label": f"予算：{_budget_display(session)}",
                "count": 8,
                "filter_key": "budget",
                "excluded_reason": "予算帯に合わない上位SUVを除外",
            },
            {
                "label": "利用シーン・価値観との一致",
                "count": final_count,
                "filter_key": "scene",
                "excluded_reason": "重視する価値軸との適合度が低い車種を除外",
            },
        ]
        exclusion_notes = [s.get("excluded_reason", "") for s in stages if s.get("excluded_reason")]

    return {
        "input": input_conditions,
        "stages": stages,
        "exclusion_notes": [n for n in exclusion_notes if n],
    }
