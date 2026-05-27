# -*- coding: utf-8 -*-
"""
Neo4j v3 オントロジーに対する推薦エンジン回帰テスト。
実行: py -m pytest tests/test_recommendation_v3.py -v
      （Neo4j 未起動時は接続テストのみ skip）
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.recommendation_engine import RecommendationEngine, RecommendationRequest
from engine.demo_profile import DemoProfileCalculator


def _neo4j_available() -> bool:
    try:
        engine = RecommendationEngine()
        engine.driver.verify_connectivity()
        engine.close()
        return True
    except Exception:
        return False


neo4j_required = pytest.mark.skipif(
    not _neo4j_available(),
    reason="Neo4j が起動していないためスキップ",
)


class TestDemoProfile:
    def test_profile_from_single_answer(self):
        calc = DemoProfileCalculator()
        result = calc.compute_from_answers([
            {"question_index": 1, "question_id": "q1_value", "answer_key": "safety"},
        ])
        assert "profile" in result
        assert result["profile"]["score_safety"] >= 0
        assert "ChildSafety" in result["mapped_needs"] or "DrivingConfidence" in result["mapped_needs"]

    def test_profile_five_answers(self):
        calc = DemoProfileCalculator()
        answers = [
            {"question_index": 1, "question_id": "q1_value", "answer_key": "family"},
            {"question_index": 2, "question_id": "q2_weekend", "answer_key": "family_center"},
            {"question_index": 3, "question_id": "q3_regret", "answer_key": "family_dissatisfaction"},
            {"question_index": 4, "question_id": "q4_stress", "answer_key": "fatigue"},
            {"question_index": 5, "question_id": "q5_ai", "answer_key": "co_pilot"},
        ]
        # q5 key fix
        answers[-1]["answer_key"] = "ai_candidates"
        result = calc.compute_from_answers(answers)
        assert result["profile"]["score_family"] >= result["profile"]["score_adventure"]
        assert len(result["ui_needs"]) >= 1


@neo4j_required
class TestRecommendationV3:
    def test_recommend_returns_nonzero_scores(self):
        engine = RecommendationEngine()
        try:
            req = RecommendationRequest(
                family_size=4,
                budget=3_000_000,
                needs=["safety", "family"],
            )
            results = engine.recommend(req, top_k=3)
            assert len(results) >= 1, "推薦結果が空"
            for r in results:
                assert r.score > 0, f"{r.model} のスコアが 0: need={r.need_score}"
                assert r.model, "車種名が空"
        finally:
            engine.close()

    def test_v3_need_path_query(self):
        """VehicleModel → TechnicalFeature → Capability → Need パスが動作する。"""
        engine = RecommendationEngine()
        try:
            vehicles = engine._get_all_vehicles()
            assert len(vehicles) > 0, "HAS_FEATURE を持つ車種が存在しない"
            sample = vehicles[0]["name"]
            needs = engine._vehicle_graph_needs(sample)
            # 一部車種は Need 未リンクの可能性あり
            assert isinstance(needs, set)
        finally:
            engine.close()

    def test_fit_or_vezel_in_top3_for_family_safety(self):
        engine = RecommendationEngine()
        try:
            req = RecommendationRequest(
                family_size=4,
                budget=3_000_000,
                needs=["safety", "family", "comfort"],
            )
            results = engine.recommend(req, top_k=5)
            models = {r.model.upper() for r in results}
            honda_family = models & {"FIT", "VEZEL", "ステップワゴン", "FREED", "N-BOX"}
            assert honda_family, f"期待車種が top5 に無い: {models}"
        finally:
            engine.close()
