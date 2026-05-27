# -*- coding: utf-8 -*-
"""Phase 2: graph-path API"""
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


class TestPhase2GraphPath:
    def test_graph_path_structure(self):
        sid = _session_with_5_answers()
        r = client.get(f"/api/demo/sessions/{sid}/graph-path")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert "why_panel" in data
        assert len(data["nodes"]) >= 5
        assert len(data["edges"]) >= 4
        types = {n["type"] for n in data["nodes"]}
        assert "person" in types
        assert "vehicle" in types

    def test_graph_path_personalizes_why_panel(self):
        sid = _session_with_5_answers()
        data = client.get(f"/api/demo/sessions/{sid}/graph-path").json()
        values = data["why_panel"]["values"]
        assert len(values) >= 2
        assert values[0]["percent"] >= values[-1]["percent"]
        assert data["why_panel"]["logic"]

    def test_graph_path_top_model_query(self):
        sid = _session_with_5_answers()
        r = client.get(f"/api/demo/sessions/{sid}/graph-path?top_model=FIT")
        assert r.status_code == 200
        vehicles = [n for n in r.json()["nodes"] if n["type"] == "vehicle"]
        assert any(n["label"] == "FIT" for n in vehicles)

    def test_graph_path_not_found(self):
        r = client.get("/api/demo/sessions/nonexistent/graph-path")
        assert r.status_code == 404
