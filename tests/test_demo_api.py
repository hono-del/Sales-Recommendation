# -*- coding: utf-8 -*-
"""デモ API のユニットテスト（Neo4j 不要）"""
from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.api_server import app

client = TestClient(app)


class TestDemoAPI:
    def test_health_includes_neo4j_field(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["neo4j"] in ("connected", "unavailable")

    def test_create_session(self):
        r = client.post("/api/demo/sessions", json={})
        assert r.status_code == 201
        body = r.json()
        assert "session_id" in body
        assert body["status"] == "active"

    def test_answer_updates_profile(self):
        sess = client.post("/api/demo/sessions", json={}).json()
        sid = sess["session_id"]
        r = client.post(
            f"/api/demo/sessions/{sid}/answers",
            json={
                "question_index": 1,
                "question_id": "q1_value",
                "answer_key": "safety",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["profile"]["score_safety"] > 0
        assert len(data["mapped_needs"]) > 0

    def test_delegation(self):
        sess = client.post("/api/demo/sessions", json={}).json()
        sid = sess["session_id"]
        r = client.patch(
            f"/api/demo/sessions/{sid}/delegation",
            json={"delegation_level": "co_pilot"},
        )
        assert r.status_code == 200
        assert r.json()["delegation_level"] == "co_pilot"

    def test_questions_master(self):
        r = client.get("/api/demo/questions")
        assert r.status_code == 200
        assert len(r.json()["questions"]) == 5

    def test_fallback_recommend(self):
        r = client.get("/api/demo/fallback/recommend")
        assert r.status_code == 200
        assert len(r.json()["recommendations"]) == 3
