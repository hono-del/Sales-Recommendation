"""
Quick Questions 回答からプロファイルスコア・Need/Capability マッピングを算出する。
config/score-weights.json と config/need-mapping.json を使用。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_AXES = ("safety", "family", "efficiency", "enjoyment", "adventure")


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


class DemoProfileCalculator:
    def __init__(self) -> None:
        self._weights = _load_json("score-weights.json")
        self._mapping = _load_json("need-mapping.json")

    def compute_from_answers(
        self, answers: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        answers: [{ "question_id": "q1_value", "answer_key": "safety" }, ...]
        """
        raw_scores: dict[str, float] = {axis: 0.0 for axis in _AXES}
        decay = float(self._weights.get("decay_per_question", 1.0))
        answer_weights: dict = self._weights.get("answer_weights", {})
        load_labels: dict = self._weights.get("load_labels", {})
        answer_to_needs: dict = self._mapping.get("answer_to_needs", {})
        need_to_cap: dict = self._mapping.get("need_to_capabilities", {})

        needs_set: set[str] = set()
        loads: list[str] = []
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

            if key in load_labels and load_labels[key] not in loads:
                loads.append(load_labels[key])

        profile_scores = _normalize_scores(raw_scores)
        capabilities: list[str] = []
        cap_seen: set[str] = set()
        for need in sorted(needs_set):
            cap = need_to_cap.get(need)
            if cap and cap not in cap_seen:
                cap_seen.add(cap)
                capabilities.append(cap)

        ui_needs = self.profile_to_ui_needs(profile_scores)

        return {
            "profile": {
                "score_safety": profile_scores["safety"],
                "score_family": profile_scores["family"],
                "score_efficiency": profile_scores["efficiency"],
                "score_enjoyment": profile_scores["enjoyment"],
                "score_adventure": profile_scores["adventure"],
            },
            "mapped_needs": sorted(needs_set),
            "mapped_capabilities": capabilities,
            "detected_loads": loads,
            "ui_needs": ui_needs,
        }

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
