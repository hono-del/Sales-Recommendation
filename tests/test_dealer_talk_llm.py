"""
Claude API 統合テスト — Dealer Talk LLM 生成
"""
import os
import pytest
import httpx


API_URL = "http://localhost:8000"
TIMEOUT = 30.0


@pytest.fixture
def session_id():
    """テスト用セッション作成"""
    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        resp = client.post("/api/demo/sessions")
        assert resp.status_code == 201
        data = resp.json()
        return data["session_id"]


def test_dealer_talk_with_llm(session_id):
    """
    LLM による dealer-talk 生成のテスト
    """
    # 1. セッションに回答を登録
    questions = [
        {"question_index": 1, "question_id": "q1_usage", "answer_key": "family"},
        {"question_index": 2, "question_id": "q2_priority", "answer_key": "safety"},
        {"question_index": 3, "question_id": "q3_load", "answer_key": "後悔不安"},
        {"question_index": 4, "question_id": "q4_style", "answer_key": "徹底比較派"},
        {"question_index": 5, "question_id": "q5_vehicle", "answer_key": "minivan"},
    ]

    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        for q in questions:
            resp = client.post(f"/api/demo/sessions/{session_id}/answers", json=q)
            assert resp.status_code == 200

        # 2. 推薦取得
        resp = client.post(f"/api/demo/sessions/{session_id}/recommend")
        assert resp.status_code == 200
        recommend_data = resp.json()
        top_model = recommend_data["recommendations"][0]["model"]

        # 3. Dealer Talk 生成
        resp = client.post(
            f"/api/demo/sessions/{session_id}/dealer-talk",
            json={"top_model": top_model, "delegation_level": "co_pilot"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # 4. レスポンス構造検証
        assert "insight" in data
        assert "talk_script" in data
        assert "generated_by" in data

        insight = data["insight"]
        assert "customer_type" in insight
        assert "scenes" in insight
        assert "anxieties" in insight
        assert "values" in insight

        # 5. LLM 生成確認（API キーがある場合）
        if os.environ.get("ANTHROPIC_API_KEY"):
            assert data["generated_by"] == "llm"
            # LLM 生成はテンプレートより長いことが期待される
            assert len(data["talk_script"]) > 100
            print(f"\n[OK] LLM 生成成功 ({len(data['talk_script'])} 文字)")
            print(f"トーク: {data['talk_script'][:200]}...")
        else:
            # API キーがない場合はテンプレートフォールバック
            assert data["generated_by"] == "template"
            print("\n[WARN] API キーなし → テンプレートフォールバック")


def test_dealer_talk_delegation_levels(session_id):
    """
    委任レベル別の生成テスト
    """
    questions = [
        {"question_index": 1, "question_id": "q1_usage", "answer_key": "daily"},
        {"question_index": 2, "question_id": "q2_priority", "answer_key": "efficiency"},
        {"question_index": 3, "question_id": "q3_load", "answer_key": "維持費不安"},
        {"question_index": 4, "question_id": "q4_style", "answer_key": "十分派"},
        {"question_index": 5, "question_id": "q5_vehicle", "answer_key": "sedan"},
    ]

    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        for q in questions:
            resp = client.post(f"/api/demo/sessions/{session_id}/answers", json=q)
            assert resp.status_code == 200

        # 推薦取得
        resp = client.post(f"/api/demo/sessions/{session_id}/recommend")
        top_model = resp.json()["recommendations"][0]["model"]

        # 各委任レベルでテスト
        levels = ["guide", "co_pilot", "auto"]
        for level in levels:
            resp = client.post(
                f"/api/demo/sessions/{session_id}/dealer-talk",
                json={"top_model": top_model, "delegation_level": level},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["talk_script"]
            print(f"\n[OK] 委任レベル '{level}': {data['generated_by']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
