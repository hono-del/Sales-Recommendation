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
        """アトミック書き込み（OneDrive 同期・uvicorn reload との競合を軽減）"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._sessions, ensure_ascii=False, indent=2)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(self._path)

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
            "family_size": None,
            "budget_range": None,
            "budget_min": None,
            "budget_max": None,
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

    def set_cached_recommendations(
        self, session_id: str, payload: dict[str, Any]
    ) -> None:
        """推薦結果をセッションにキャッシュ（graph-path の二重実行防止）。"""
        session = self.require_session(session_id)
        session["cached_recommendations"] = {
            "cached_at": _iso(_utc_now()),
            "payload": payload,
        }
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
    
    def set_profile_input(
        self,
        session_id: str,
        family_size: int,
        budget_range: str,
    ) -> dict[str, Any]:
        """
        人数・予算を設定
        
        Args:
            session_id: セッション ID
            family_size: 乗車人数
            budget_range: 予算範囲（例: "300-400"）
        
        Returns:
            更新されたセッション情報
        """
        session = self.require_session(session_id)
        
        # 予算範囲をパース
        budget_min, budget_max = self._parse_budget_range(budget_range)
        
        session["family_size"] = family_size
        session["budget_range"] = budget_range
        session["budget_min"] = budget_min
        session["budget_max"] = budget_max
        session["status"] = "profile_input_complete"
        session["updated_at"] = _iso(_utc_now())
        self._save()
        
        return {
            "session_id": session_id,
            "status": session["status"],
            "family_size": family_size,
            "budget_min": budget_min,
            "budget_max": budget_max,
        }
    
    def _parse_budget_range(self, budget_range: str) -> tuple[int, int]:
        """
        予算範囲文字列を最小値・最大値に変換（単位: 円）
        
        Args:
            budget_range: 予算範囲（例: "300-400", "~200", "500~"）
        
        Returns:
            (budget_min, budget_max) in yen
        """
        budget_range = budget_range.strip()
        
        # "~200" 形式
        if budget_range.startswith("~"):
            max_val = int(budget_range[1:])
            return 0, max_val * 10_000
        
        # "500~" 形式
        if budget_range.endswith("~"):
            min_val = int(budget_range[:-1])
            return min_val * 10_000, 99_999_999
        
        # "300-400" 形式
        if "-" in budget_range:
            parts = budget_range.split("-")
            min_val = int(parts[0])
            max_val = int(parts[1])
            return min_val * 10_000, max_val * 10_000
        
        # 単一値 "300" 形式（±50万円の幅）
        val = int(budget_range)
        return (val - 50) * 10_000, (val + 50) * 10_000


_store: Optional[DemoSessionStore] = None


def get_session_store() -> DemoSessionStore:
    global _store
    if _store is None:
        _store = DemoSessionStore()
    return _store
