"""
Supabase を使ったセッションストア
ローカル環境では sessions.json、Vercel では Supabase を使用
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class SupabaseSessionStore:
    """
    ローカル: sessions.json に保存
    Vercel: Supabase (PostgreSQL) に保存
    """

    def __init__(self, json_path: str = "data/demo/sessions.json"):
        self._json_path = Path(json_path)
        self._use_supabase = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"))
        
        if self._use_supabase:
            import requests
            self._supabase_url = os.getenv("SUPABASE_URL")
            self._supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
            self._requests = requests
            print(f"[SessionStore] Using Supabase for persistence")
            self._ensure_table()
        else:
            self._sessions = self._load_from_file()
            print(f"[SessionStore] Using local file: {self._json_path}")

    def _load_from_file(self) -> dict[str, dict[str, Any]]:
        if not self._json_path.exists():
            return {}
        try:
            data = json.loads(self._json_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_to_file(self) -> None:
        self._json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._sessions, ensure_ascii=False, indent=2)
        tmp = self._json_path.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(self._json_path)

    def _ensure_table(self) -> None:
        """Supabase テーブルを作成（存在しない場合）"""
        # Note: Supabase ダッシュボードで以下のSQLを実行してください：
        # CREATE TABLE IF NOT EXISTS demo_sessions (
        #   session_id TEXT PRIMARY KEY,
        #   data JSONB NOT NULL,
        #   created_at TIMESTAMPTZ DEFAULT NOW(),
        #   updated_at TIMESTAMPTZ DEFAULT NOW()
        # );
        pass

    def _sb_get(self, session_id: str) -> Optional[dict]:
        """Supabase から取得"""
        try:
            response = self._requests.get(
                f"{self._supabase_url}/rest/v1/demo_sessions",
                headers={
                    "apikey": self._supabase_key,
                    "Authorization": f"Bearer {self._supabase_key}",
                },
                params={"session_id": f"eq.{session_id}", "select": "data"},
                timeout=5,
            )
            if response.status_code == 200:
                rows = response.json()
                return rows[0]["data"] if rows else None
            return None
        except Exception as e:
            print(f"[Supabase GET Error] {e}")
            return None

    def _sb_upsert(self, session_id: str, data: dict) -> None:
        """Supabase に保存（UPSERT）"""
        try:
            response = self._requests.post(
                f"{self._supabase_url}/rest/v1/demo_sessions",
                headers={
                    "apikey": self._supabase_key,
                    "Authorization": f"Bearer {self._supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                },
                json={
                    "session_id": session_id,
                    "data": data,
                    "updated_at": _iso(_utc_now()),
                },
                timeout=5,
            )
            response.raise_for_status()
            print(f"[Supabase UPSERT Success] session_id={session_id}")
        except Exception as e:
            print(f"[Supabase UPSERT Error] session_id={session_id}, error={e}")
            raise  # エラーを再スローして上位で処理できるようにする

    def _sb_list_all(self) -> dict[str, dict[str, Any]]:
        """Supabase から全セッション取得"""
        try:
            response = self._requests.get(
                f"{self._supabase_url}/rest/v1/demo_sessions",
                headers={
                    "apikey": self._supabase_key,
                    "Authorization": f"Bearer {self._supabase_key}",
                },
                params={"select": "session_id,data"},
                timeout=10,
            )
            if response.status_code == 200:
                rows = response.json()
                return {row["session_id"]: row["data"] for row in rows}
            return {}
        except Exception as e:
            print(f"[Supabase LIST Error] {e}")
            return {}

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        if self._use_supabase:
            return self._sb_get(session_id)
        else:
            return self._sessions.get(session_id)

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
        
        if self._use_supabase:
            self._sb_upsert(sid, session)
        else:
            self._sessions[sid] = session
            self._save_to_file()
        
        return {
            "session_id": sid,
            "created_at": session["created_at"],
            "status": "active",
        }

    def require_session(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(session_id)
        return session

    def _save_session(self, session_id: str, session: dict[str, Any]) -> None:
        """セッションを保存（共通処理）"""
        session["updated_at"] = _iso(_utc_now())
        if self._use_supabase:
            self._sb_upsert(session_id, session)
        else:
            self._sessions[session_id] = session
            self._save_to_file()

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
        self._save_session(session_id, session)
        return session

    def set_profile(self, session_id: str, profile_data: dict[str, Any]) -> None:
        session = self.require_session(session_id)
        session["profile"] = profile_data
        self._save_session(session_id, session)

    def set_cached_recommendations(
        self, session_id: str, payload: dict[str, Any]
    ) -> None:
        session = self.require_session(session_id)
        session["cached_recommendations"] = {
            "cached_at": _iso(_utc_now()),
            "payload": payload,
        }
        self._save_session(session_id, session)

    def set_delegation(self, session_id: str, level: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        session["delegation_level"] = level
        self._save_session(session_id, session)
        return {
            "session_id": session_id,
            "delegation_level": level,
            "message": "",
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
        self._save_session(session_id, session)
        return {"id": event_id, "created_at": created}

    def mark_fallback(self, session_id: str) -> None:
        session = self.require_session(session_id)
        session["demo_fallback_used"] = True
        self._save_session(session_id, session)

    def set_service_recommendations_cache(
        self, session_id: str, payload: dict[str, Any]
    ) -> None:
        session = self.require_session(session_id)
        session["service_recommendations_cache"] = payload
        self._save_session(session_id, session)

    def list_all_sessions(self) -> dict[str, dict[str, Any]]:
        """全セッション取得（分析用）"""
        if self._use_supabase:
            return self._sb_list_all()
        else:
            return self._sessions
