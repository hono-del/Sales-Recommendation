"""
Vercel KV (Redis) を使ったセッションストア
ローカル環境では sessions.json、Vercel では KV を使用
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import requests


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class VercelSessionStore:
    """
    ローカル: sessions.json に保存
    Vercel: Vercel KV (Redis) に保存
    """

    def __init__(self, json_path: str = "data/demo/sessions.json"):
        self._json_path = Path(json_path)
        self._use_kv = bool(os.getenv("KV_REST_API_URL"))
        
        if self._use_kv:
            self._kv_url = os.getenv("KV_REST_API_URL")
            self._kv_token = os.getenv("KV_REST_API_TOKEN")
            print(f"[SessionStore] Using Vercel KV for persistence")
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

    def _kv_get(self, key: str) -> Optional[dict]:
        """Vercel KV から取得"""
        try:
            response = requests.get(
                f"{self._kv_url}/get/{key}",
                headers={"Authorization": f"Bearer {self._kv_token}"},
                timeout=5,
            )
            if response.status_code == 200:
                result = response.json().get("result")
                return json.loads(result) if result else None
            return None
        except Exception as e:
            print(f"[KV GET Error] {e}")
            return None

    def _kv_set(self, key: str, value: dict) -> None:
        """Vercel KV に保存"""
        try:
            requests.post(
                f"{self._kv_url}/set/{key}",
                headers={"Authorization": f"Bearer {self._kv_token}"},
                json={"value": json.dumps(value, ensure_ascii=False)},
                timeout=5,
            )
        except Exception as e:
            print(f"[KV SET Error] {e}")

    def _kv_keys(self, pattern: str = "*") -> list[str]:
        """Vercel KV からキー一覧を取得"""
        try:
            response = requests.get(
                f"{self._kv_url}/keys/{pattern}",
                headers={"Authorization": f"Bearer {self._kv_token}"},
                timeout=5,
            )
            if response.status_code == 200:
                return response.json().get("result", [])
            return []
        except Exception as e:
            print(f"[KV KEYS Error] {e}")
            return []

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        if self._use_kv:
            return self._kv_get(f"session:{session_id}")
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
        
        if self._use_kv:
            self._kv_set(f"session:{sid}", session)
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
        if self._use_kv:
            self._kv_set(f"session:{session_id}", session)
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
        if self._use_kv:
            keys = self._kv_keys("session:*")
            sessions = {}
            for key in keys:
                sid = key.replace("session:", "")
                session = self._kv_get(key)
                if session:
                    sessions[sid] = session
            return sessions
        else:
            return self._sessions
