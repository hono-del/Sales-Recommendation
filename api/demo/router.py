"""
デモ API ルーター — /api/demo/*
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.demo.graph_path_service import get_graph_path
from api.demo.recommend_service import recommend_for_session
from api.demo.session_store import get_session_store
from engine.demo_profile import DemoProfileCalculator

router = APIRouter(prefix="/api/demo", tags=["demo"])

_FALLBACK_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "fallback"
_calculator = DemoProfileCalculator()


# ── Request models ─────────────────────────────────────────────────────────

class AnswerRequest(BaseModel):
    question_index: int = Field(..., ge=1, le=5)
    question_id: str
    answer_key: str


class DelegationRequest(BaseModel):
    delegation_level: str = Field(..., pattern="^(guide|co_pilot|auto)$")


class EventRequest(BaseModel):
    screen_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[int] = None


class DealerTalkRequest(BaseModel):
    top_model: str = ""
    delegation_level: str = "co_pilot"


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("/questions")
def list_questions():
    """Quick Questions マスタを返す。"""
    path = Path(__file__).resolve().parent.parent.parent / "config" / "questions.json"
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/sessions", status_code=201)
def create_session():
    store = get_session_store()
    return store.create_session()


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    store = get_session_store()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return {
        "session_id": session_id,
        "status": session["status"],
        "delegation_level": session.get("delegation_level"),
        "answers_count": len(session.get("answers", [])),
        "profile": session.get("profile"),
        "demo_fallback_used": session.get("demo_fallback_used", False),
    }


@router.post("/sessions/{session_id}/answers")
def post_answer(session_id: str, body: AnswerRequest):
    store = get_session_store()
    try:
        session = store.upsert_answer(
            session_id,
            body.question_index,
            body.question_id,
            body.answer_key,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    computed = _calculator.compute_from_answers(session["answers"])
    store.set_profile(session_id, computed)

    return {
        "session_id": session_id,
        "profile": computed["profile"],
        "mapped_needs": computed["mapped_needs"],
        "mapped_capabilities": computed["mapped_capabilities"],
        "detected_loads": computed["detected_loads"],
    }


@router.patch("/sessions/{session_id}/delegation")
def patch_delegation(session_id: str, body: DelegationRequest):
    store = get_session_store()
    try:
        return store.set_delegation(session_id, body.delegation_level)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@router.get("/sessions/{session_id}/graph-path")
def get_session_graph_path(session_id: str, top_model: Optional[str] = None):
    store = get_session_store()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    data = get_graph_path(session, session_id=session_id, top_model=top_model)
    if data.get("demo_fallback"):
        store.mark_fallback(session_id)
    return data


@router.post("/sessions/{session_id}/events", status_code=201)
def post_event(session_id: str, body: EventRequest):
    store = get_session_store()
    try:
        return store.add_event(
            session_id,
            body.screen_id,
            body.event_type,
            body.payload,
            body.duration_ms,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@router.post("/sessions/{session_id}/recommend")
def post_session_recommend(session_id: str):
    """セッションプロファイルに基づく推薦（top3 + excluded）。"""
    store = get_session_store()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    answer_count = len(session.get("answers", []))
    has_profile = bool(session.get("profile"))
    if answer_count < 5 and not has_profile:
        raise HTTPException(
            status_code=400,
            detail="5問すべて回答してから推薦を取得してください",
        )

    result = recommend_for_session(session)
    if result["demo_fallback"]:
        store.mark_fallback(session_id)

    return {
        "session_id": session_id,
        **result,
    }


@router.post("/sessions/{session_id}/dealer-talk")
def post_dealer_talk(session_id: str, body: DealerTalkRequest):
    """販売店向けインサイトとトークスクリプト（テンプレート生成）。"""
    store = get_session_store()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    profile_data = session.get("profile") or {}
    prof = profile_data.get("profile") or {}
    loads = profile_data.get("detected_loads") or []
    top_model = body.top_model or "おすすめ車種"

    scores = [
        ("安心", prof.get("score_safety", 0)),
        ("家族", prof.get("score_family", 0)),
        ("効率", prof.get("score_efficiency", 0)),
        ("楽しさ", prof.get("score_enjoyment", 0)),
    ]
    scores.sort(key=lambda x: -x[1])
    top_values = [s[0] for s in scores[:3]]

    customer_type = "家族重視" if prof.get("score_family", 0) >= prof.get("score_safety", 0) else "安心重視"
    scenes = []
    if prof.get("score_family", 0) > 60:
        scenes.append("週末ファミリー")
    if prof.get("score_efficiency", 0) > 55:
        scenes.append("日常・通勤")
    if not scenes:
        scenes = ["日常利用"]

    anxieties = loads[:3] if loads else ["後悔", "維持費", "家族の満足"]
    values = top_values

    talk = (
        f"「{top_values[0]}」を特に重視されているとのことです。"
        f"そのため {top_model} は、スペック比較だけでなく、"
        f"{'・'.join(anxieties[:2])}への不安をどう和らげるかがポイントになります。\n\n"
        f"同様の価値観を持つ購入者の多くが、"
        f"試乗後に「{top_values[1] if len(top_values) > 1 else '使いやすさ'}」を実感しています。"
        f"次のステップとして、ご家族での試乗をご提案してみてはいかがでしょうか。"
    )

    return {
        "insight": {
            "customer_type": customer_type,
            "scenes": scenes,
            "anxieties": anxieties,
            "values": values,
        },
        "talk_script": talk,
        "generated_by": "template",
    }


@router.get("/fallback/recommend")
def fallback_recommend():
    """Neo4j 不可時の固定推薦 JSON。"""
    path = _FALLBACK_DIR / "recommend.json"
    return json.loads(path.read_text(encoding="utf-8"))
