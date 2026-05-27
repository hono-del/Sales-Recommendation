# -*- coding: utf-8 -*-
"""Phase 1: セッション推薦 API"""
from __future__ import annotations

import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.api_server import app

client = TestClient(app)


def _session_with_5_answers() -> str:
    sid = client.post("/api/demo/sessions", json={}).json()["session_id"]
    answers = [
        (1, "q1_value", "family"),
        (2, "q2_weekend", "family_center"),
        (3, "q3_regret", "family_dissatisfaction"),
        (4, "q4_stress", "fatigue"),
        (5, "q5_ai", "ai_candidates"),
    ]
    for qi, qid, key in answers:
        client.post(
            f"/api/demo/sessions/{sid}/answers",
            json={"question_index": qi, "question_id": qid, "answer_key": key},
        )
    return sid


class TestPhase1Recommend:
    def test_recommend_requires_5_answers(self):
        sid = client.post("/api/demo/sessions", json={}).json()["session_id"]
        r = client.post(f"/api/demo/sessions/{sid}/recommend")
        assert r.status_code == 400

    def test_recommend_returns_top3(self):
        sid = _session_with_5_answers()
        r = client.post(f"/api/demo/sessions/{sid}/recommend")
        assert r.status_code == 200
        data = r.json()
        assert len(data["recommendations"]) == 3
        assert data["recommendations"][0]["score"] > 0
        assert "archetype" in data["recommendations"][0]
        assert "demo_fallback" in data
        assert len(data["excluded"]) <= 3
        if data["recommendations"][0].get("appeal_points") is not None:
            assert isinstance(data["recommendations"][0]["appeal_points"], list)

    def test_recommend_excluded_up_to_three(self):
        sid = _session_with_5_answers()
        data = client.post(f"/api/demo/sessions/{sid}/recommend").json()
        excluded = data["excluded"]
        assert 1 <= len(excluded) <= 3
        models = {r["model"] for r in data["recommendations"]}
        for ex in excluded:
            assert ex["model"] not in models
            assert ex.get("reason")
