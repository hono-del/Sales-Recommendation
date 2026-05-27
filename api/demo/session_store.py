"""
デモセッション永続化（JSON ファイル）。
API 再起動後もセッションを保持する。
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_SESSIONS_FILE = (
    Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "sessions.json"
)

_DELEGATION_MESSAGES = {
    "guide": "AIは候補を提示します。最終判断はあなたにお任せします。",
    "co_pilot": "AIが伴走しながら、一緒に納得解を探します。",
    "auto": "AIが最適案を提案します。理由もあわせてご確認ください。",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class DemoSessionStore:
    """JSON ファイル永続化セッションストア。"""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _SESSIONS_FILE
        self._sessions: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._sessions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def create_session(self) -> dict[str, Any]:
        sid = str(uuid.uuid4())
        now = _utc_now()
        session = {
            "session_id": sid,
            "created_at": _iso(now),
            "updated_at": _iso(now),
            "status": "active",
            "delegation_level": None,
            "demo_fallback_used": False,
            "answers": [],
            "profile": None,
            "events": [],
        }
        self._sessions[sid] = session
        self._save()
        return {
            "session_id": sid,
            "created_at": session["created_at"],
            "status": "active",
        }

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        return self._sessions.get(session_id)

    def require_session(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(session_id)
        return session

    def upsert_answer(
        self,
        session_id: str,
        question_index: int,
        question_id: str,
        answer_key: str,
    ) -> dict[str, Any]:
        session = self.require_session(session_id)
        answers: list[dict] = session["answers"]
        answers = [a for a in answers if a.get("question_index") != question_index]
        answers.append({
            "question_index": question_index,
            "question_id": question_id,
            "answer_key": answer_key,
            "answered_at": _iso(_utc_now()),
        })
        session["answers"] = sorted(answers, key=lambda a: a["question_index"])
        session["updated_at"] = _iso(_utc_now())
        self._save()
        return session

    def set_profile(self, session_id: str, profile_data: dict[str, Any]) -> None:
        session = self.require_session(session_id)
        session["profile"] = profile_data
        session["updated_at"] = _iso(_utc_now())
        self._save()

    def set_delegation(self, session_id: str, level: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        session["delegation_level"] = level
        session["updated_at"] = _iso(_utc_now())
        self._save()
        return {
            "session_id": session_id,
            "delegation_level": level,
            "message": _DELEGATION_MESSAGES.get(level, ""),
        }

    def add_event(
        self,
        session_id: str,
        screen_id: str,
        event_type: str,
        payload: Optional[dict] = None,
        duration_ms: Optional[int] = None,
    ) -> dict[str, Any]:
        session = self.require_session(session_id)
        event_id = str(uuid.uuid4())
        created = _iso(_utc_now())
        event = {
            "id": event_id,
            "screen_id": screen_id,
            "event_type": event_type,
            "payload": payload or {},
            "duration_ms": duration_ms,
            "created_at": created,
        }
        session["events"].append(event)
        session["updated_at"] = created
        self._save()
        return {"id": event_id, "created_at": created}

    def mark_fallback(self, session_id: str) -> None:
        session = self.require_session(session_id)
        session["demo_fallback_used"] = True
        self._save()


_store: Optional[DemoSessionStore] = None


def get_session_store() -> DemoSessionStore:
    global _store
    if _store is None:
        _store = DemoSessionStore()
    return _store
