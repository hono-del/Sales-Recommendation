"""
Quick Questions 回答からプロファイルスコア・Need/Capability マッピングを算出する。
config/score-weights.json と config/need-mapping.json を使用。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.kg_need_resolver import graph_need_names, resolve_kg_needs, ui_needs_from_kg_needs

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_AXES = ("safety", "family", "efficiency", "enjoyment", "adventure")

_DEFAULT_STYLE = "Satisficer"


def _load_json(name: str) -> dict[str, Any]:
    path = _CONFIG_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def _normalize_scores(raw: dict[str, float]) -> dict[str, float]:
    """最大値を 100 にスケール（全 0 の場合はベースライン）。"""
    peak = max(raw.values()) if raw else 0.0
    if peak <= 0:
        return {axis: 20.0 for axis in _AXES}
    return {axis: _clamp_score((raw.get(axis, 0.0) / peak) * 100.0) for axis in _AXES}


def _answers_by_qid(answers: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(a.get("question_id", "")): str(a.get("answer_key", ""))
        for a in answers
        if a.get("question_id")
    }


class DemoProfileCalculator:
    def __init__(self) -> None:
        self._weights = _load_json("score-weights.json")
        self._mapping = _load_json("need-mapping.json")
        self._style_weights = _load_json("decision-style-weights.json")
        self._load_rules = _load_json("load-detection-rules.json")

    def compute_from_answers(
        self, answers: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        answers: [{ "question_id": "q1_value", "answer_key": "safety" }, ...]
        """
        raw_scores: dict[str, float] = {axis: 0.0 for axis in _AXES}
        decay = float(self._weights.get("decay_per_question", 1.0))
        answer_weights: dict = self._weights.get("answer_weights", {})
        answer_to_needs: dict = self._mapping.get("answer_to_needs", {})
        need_to_cap: dict = self._mapping.get("need_to_capabilities", {})

        needs_set: set[str] = set()
        need_sources: dict[str, list[dict[str, str]]] = {}  # Need → 導出元の回答リスト
        sorted_answers = sorted(answers, key=lambda a: a.get("question_index", 0))

        for i, ans in enumerate(sorted_answers):
            qid = ans.get("question_id", "")
            key = ans.get("answer_key", "")
            factor = decay ** (len(sorted_answers) - 1 - i)

            q_weights = answer_weights.get(qid, {}).get(key, {})
            for axis, delta in q_weights.items():
                if axis in raw_scores:
                    raw_scores[axis] += float(delta) * factor

            for need in answer_to_needs.get(qid, {}).get(key, []):
                needs_set.add(need)
                # ニーズの導出元を記録
                if need not in need_sources:
                    need_sources[need] = []
                need_sources[need].append({
                    "question_id": qid,
                    "answer_key": key,
                })
        
        profile_scores = _normalize_scores(raw_scores)
        
        # ルールベースLoad検出（profile_scoresを渡す）
        load_details = self._detect_loads_from_rules(sorted_answers, profile_scores)
        load_names = [load["name"] for load in load_details]
        style_result = self.compute_decision_style(answers)

        kg_needs = resolve_kg_needs(profile_scores, load_names, sorted_answers)
        kg_need_names_list = graph_need_names(kg_needs)
        for n in sorted(needs_set):
            if n not in kg_need_names_list:
                kg_need_names_list.append(n)

        capabilities: list[str] = []
        cap_seen: set[str] = set()
        for need in kg_need_names_list:
            cap = need_to_cap.get(need)
            if cap and cap not in cap_seen:
                cap_seen.add(cap)
                capabilities.append(cap)

        ui_needs = ui_needs_from_kg_needs(kg_needs, profile_scores, self._mapping)

        # ニーズ → 価値観軸のマッピングを作成
        need_to_values: dict[str, list[str]] = {}
        for need, sources in need_sources.items():
            value_axes: set[str] = set()
            for source in sources:
                qid = source["question_id"]
                key = source["answer_key"]
                # この回答がどの価値観軸に寄与しているかを取得
                q_weights = answer_weights.get(qid, {}).get(key, {})
                for axis, delta in q_weights.items():
                    if axis in _AXES and float(delta) > 0:
                        value_axes.add(axis)
            need_to_values[need] = list(value_axes)

        return {
            "profile": {
                "score_safety": profile_scores["safety"],
                "score_family": profile_scores["family"],
                "score_efficiency": profile_scores["efficiency"],
                "score_enjoyment": profile_scores["enjoyment"],
                "score_adventure": profile_scores["adventure"],
            },
            "mapped_needs": kg_need_names_list,
            "kg_needs": kg_needs,
            "mapped_capabilities": capabilities,
            "detected_loads": load_details,  # Load詳細情報を含む
            "ui_needs": ui_needs,
            "need_sources": need_sources,  # ニーズの導出元情報
            "need_to_values": need_to_values,  # ニーズ → 価値観軸のマッピング
            **style_result,
        }

    def compute_decision_style(self, answers: list[dict[str, Any]]) -> dict[str, Any]:
        """Quick Questions 回答から DecisionStyle（KG 6 型）を推定。"""
        cfg = self._style_weights
        styles: list[str] = list(cfg.get("styles", []))
        labels: dict[str, dict[str, str]] = cfg.get("labels", {})
        answer_weights: dict = cfg.get("answer_weights", {})
        decay = float(cfg.get("decay_per_question", 0.92))
        tie_order: list[str] = list(cfg.get("tie_break_order", styles))

        raw: dict[str, float] = {s: 0.0 for s in styles}
        sorted_answers = sorted(answers, key=lambda a: a.get("question_index", 0))

        for i, ans in enumerate(sorted_answers):
            qid = ans.get("question_id", "")
            key = ans.get("answer_key", "")
            factor = decay ** (len(sorted_answers) - 1 - i)
            deltas = answer_weights.get(qid, {}).get(key, {})
            for style, delta in deltas.items():
                if style in raw:
                    raw[style] += float(delta) * factor

        peak = max(raw.values()) if raw else 0.0
        if peak <= 0:
            return {
                "decision_style": None,
                "decision_style_label": None,
                "decision_style_description": None,
                "decision_style_scores": None,
                "decision_style_confidence": None,
                "decision_style_secondary": None,
                "decision_style_secondary_label": None,
                "decision_style_is_mixed": False,
            }

        scores = {
            s: _clamp_score((raw.get(s, 0.0) / peak) * 100.0) for s in styles
        }

        scores = self._apply_decision_style_guards(scores, _answers_by_qid(sorted_answers))

        ranked = sorted(
            scores.items(),
            key=lambda x: (-x[1], tie_order.index(x[0]) if x[0] in tie_order else 99),
        )
        primary = ranked[0][0]
        secondary = ranked[1][0] if len(ranked) > 1 else primary
        margin = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else ranked[0][1]
        confidence = _clamp_score(min(100.0, margin * 2.5))
        is_mixed = confidence < 30.0

        meta = labels.get(primary, {})
        sec_meta = labels.get(secondary, {})

        return {
            "decision_style": primary,
            "decision_style_label": meta.get("label", primary),
            "decision_style_description": meta.get("description", ""),
            "decision_style_scores": scores,
            "decision_style_confidence": confidence,
            "decision_style_secondary": secondary,
            "decision_style_secondary_label": sec_meta.get("label", secondary),
            "decision_style_is_mixed": is_mixed,
        }

    def _apply_decision_style_guards(
        self,
        scores: dict[str, float],
        by_qid: dict[str, str],
    ) -> dict[str, float]:
        """Delegator / Impulsive の過剰判定を抑制。"""
        adjusted = dict(scores)
        q5 = by_qid.get("q5_ai", "")
        q6 = by_qid.get("q6_decision_process", "")
        q7 = by_qid.get("q7_info_preference", "")

        delegator_ok = (
            q6 == "ask_others"
            or q7 == "people_pick"
            or (q5 == "ai_decide" and q7 == "shortlist")
        )

        def _rerank() -> list[tuple[str, float]]:
            return sorted(adjusted.items(), key=lambda x: -x[1])

        ranked = _rerank()
        if ranked and ranked[0][0] == "Delegator" and not delegator_ok:
            adjusted["Delegator"] = min(adjusted.values()) * 0.3

        ranked = _rerank()
        if ranked and ranked[0][0] == "Impulsive" and q6 != "quick_deal":
            second_score = ranked[1][1] if len(ranked) > 1 else 0.0
            adjusted["Impulsive"] = max(0.0, second_score - 1.0)

        return adjusted

    def profile_to_ui_needs(self, profile_scores: dict[str, float]) -> list[str]:
        """推薦 API 用の UI needs キー（上位 3 軸）。"""
        profile_map: dict = self._mapping.get("profile_to_ui_needs", {})
        ranked = sorted(profile_scores.items(), key=lambda x: -x[1])
        ui: list[str] = []
        for axis, _ in ranked[:3]:
            need_key = profile_map.get(axis)
            if need_key and need_key not in ui:
                ui.append(need_key)
        return ui or ["safety", "family", "comfort"]
    
    def _detect_loads_from_rules(self, answers: list[dict[str, Any]], profile_scores: dict[str, float]) -> list[dict[str, Any]]:
        """ルールベースでLoadsを検出し、詳細情報を返す。"""
        rules = self._load_rules.get("detection_rules", {})
        answer_map = {
            ans.get("question_id"): ans.get("answer_key")
            for ans in answers
        }
        
        answer_weights: dict = self._weights.get("answer_weights", {})
        detected_loads: list[dict[str, Any]] = []
        
        for load_name, rule in rules.items():
            triggers = rule.get("triggers", [])
            threshold = rule.get("threshold", 1)
            description = rule.get("description", "")
            match_count = 0
            matched_questions: list[str] = []
            related_values: set[str] = set()
            
            for trigger in triggers:
                q_id = trigger.get("question_id")
                answer_keys = trigger.get("answer_keys", [])
                
                if q_id in answer_map and answer_map[q_id] in answer_keys:
                    match_count += 1
                    matched_questions.append(q_id)
                    
                    # この回答が寄与する価値観軸を取得
                    answer_key = answer_map[q_id]
                    q_weights = answer_weights.get(q_id, {}).get(answer_key, {})
                    for axis, delta in q_weights.items():
                        if axis in _AXES and float(delta) > 0:
                            related_values.add(axis)
            
            if match_count >= threshold:
                # 関連する価値観を日本語ラベルに変換
                value_labels_map = {
                    "safety": "安全・安心",
                    "family": "家族との時間",
                    "efficiency": "効率・合理性",
                    "enjoyment": "楽しさ・充実感",
                    "adventure": "自己成長・学び",
                }
                related_value_labels = [value_labels_map.get(v, v) for v in related_values]
                
                detected_loads.append({
                    "name": load_name,
                    "description": description,
                    "related_values": related_value_labels,
                    "trigger_count": match_count,
                    "threshold": threshold,
                })
        
        return detected_loads
