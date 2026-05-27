"""
デモ API ルーター — /api/demo/*
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from anthropic import Anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.demo.graph_path_service import get_graph_path
from api.demo.recommend_service import recommend_for_session
from api.demo.session_store import get_session_store
from engine.demo_profile import DemoProfileCalculator

router = APIRouter(prefix="/api/demo", tags=["demo"])

_FALLBACK_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "fallback"
_calculator = DemoProfileCalculator()

# Anthropic Claude クライアント初期化
_anthropic_client = None
try:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        _anthropic_client = Anthropic(api_key=api_key)
        print(f"[INFO] Anthropic client initialized with API key: {api_key[:10]}...")
    else:
        print("[WARN] ANTHROPIC_API_KEY not found in environment variables")
except Exception as e:
    print(f"[ERROR] Failed to initialize Anthropic client: {e}")


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
    """販売店向けインサイトとトークスクリプト（LLM 生成 / テンプレート fallback）。"""
    store = get_session_store()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    profile_data = session.get("profile") or {}
    prof = profile_data.get("profile") or {}
    loads = profile_data.get("detected_loads") or []
    mapped_needs = profile_data.get("mapped_needs") or []
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

    insight = {
        "customer_type": customer_type,
        "scenes": scenes,
        "anxieties": anxieties,
        "values": values,
    }

    # LLM による生成を試みる
    talk_script, generated_by = _generate_dealer_talk_llm(
        insight=insight,
        top_model=top_model,
        top_values=top_values,
        anxieties=anxieties,
        mapped_needs=mapped_needs,
        delegation_level=body.delegation_level,
    )

    return {
        "insight": insight,
        "talk_script": talk_script,
        "generated_by": generated_by,
    }


def _generate_dealer_talk_llm(
    insight: dict,
    top_model: str,
    top_values: list[str],
    anxieties: list[str],
    mapped_needs: list[dict],
    delegation_level: str,
) -> tuple[str, str]:
    """Claude API でトークスクリプトを生成。失敗時はテンプレートを返す。"""
    
    # Claude API が利用不可の場合はテンプレートを返す
    if not _anthropic_client:
        return _generate_template_talk(top_model, top_values, anxieties), "template"

    try:
        # プロンプト構築
        # mapped_needs は文字列のリスト（例: ["DrivingConfidence", "FamilyComfort"]）
        if mapped_needs and isinstance(mapped_needs[0], dict):
            needs_text = "\n".join([f"- {n.get('need_label', n.get('need_name', ''))}" for n in mapped_needs[:5]])
        else:
            # 文字列のリストの場合はそのまま使用
            needs_text = "\n".join([f"- {n}" for n in mapped_needs[:5]])
        
        delegation_context = {
            "guide": "販売員が主導して提案する形で、顧客の悩みや不安に寄り添いながら、試乗や次のステップへ誘導する",
            "co_pilot": "顧客と販売員が協力して最適な選択を見つける形で、質問を投げかけながら対話的に進める",
            "auto": "システムが最適な提案を行う形で、データに基づく客観的な推薦理由を明確に示す",
        }
        
        prompt = f"""あなたは Honda の販売店スタッフ向けのトークスクリプト生成 AI です。
以下の顧客プロファイルに基づき、効果的な提案トークを生成してください。

【顧客プロファイル】
- タイプ: {insight['customer_type']}
- 重視する価値観（上位3つ）: {', '.join(top_values)}
- 主な不安・懸念: {', '.join(anxieties)}
- 想定利用シーン: {', '.join(insight['scenes'])}
- 顧客の生活ニーズ:
{needs_text or '（データなし）'}

【推薦車種】
{top_model}

【委任レベル】
{delegation_level} — {delegation_context.get(delegation_level, '')}

【出力要件】
1. 2-4段落、200-300文字程度の自然な会話トーン
2. 顧客の不安に寄り添いつつ、推薦車種の価値を伝える
3. 次のアクション（試乗、グレード相談など）への自然な誘導を含める
4. データや過去の購入者の声を引用する形で信頼性を高める
5. 押し付けがましくなく、顧客が主体的に判断できるような表現
6. 委任レベルに応じたトーンで記述する

トークスクリプトのみを出力してください（前置きや説明は不要）。"""

        # Claude API 呼び出し
        message = _anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        
        talk_script = message.content[0].text.strip()
        return talk_script, "llm"

    except Exception as e:
        print(f"[WARN] Claude API 呼び出し失敗、テンプレートにフォールバック: {e}")
        return _generate_template_talk(top_model, top_values, anxieties), "template"


def _generate_template_talk(
    top_model: str,
    top_values: list[str],
    anxieties: list[str],
) -> str:
    """テンプレートベースのトーク生成（フォールバック）。"""
    return (
        f"「{top_values[0]}」を特に重視されているとのことです。"
        f"そのため {top_model} は、スペック比較だけでなく、"
        f"{'・'.join(anxieties[:2])}への不安をどう和らげるかがポイントになります。\n\n"
        f"同様の価値観を持つ購入者の多くが、"
        f"試乗後に「{top_values[1] if len(top_values) > 1 else '使いやすさ'}」を実感しています。"
        f"次のステップとして、ご家族での試乗をご提案してみてはいかがでしょうか。"
    )


@router.get("/fallback/recommend")
def fallback_recommend():
    """Neo4j 不可時の固定推薦 JSON。"""
    path = _FALLBACK_DIR / "recommend.json"
    return json.loads(path.read_text(encoding="utf-8"))
