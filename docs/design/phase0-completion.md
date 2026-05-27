# Phase 0 完了チェックリスト

> **完了日**: 2026-05-26

## 成果物

| 項目 | パス | 状態 |
|------|------|------|
| Quick Questions マスタ | `config/questions.json` | ✅ |
| スコア重み | `config/score-weights.json` | ✅ |
| Need マッピング | `config/need-mapping.json` | ✅ |
| プロファイル計算 | `engine/demo_profile.py` | ✅ |
| デモ API | `api/demo/router.py` | ✅ |
| fallback JSON | `data/demo/fallback/*.json` | ✅ |
| Supabase migration | `supabase/migrations/001_demo_sessions.sql` | ✅ |
| 回帰テスト | `tests/test_recommendation_v3.py` | ✅ |
| API テスト | `tests/test_demo_api.py` | ✅ |
| Next.js 雛形 | `demo-web/` | ✅ |

## 起動手順

### 1. API（FastAPI）

```powershell
cd "C:\Users\a01380\OneDrive - CMC Corporation\デスクトップ\次世代商談"
$env:NEO4J_PASSWORD="recommendation"
py -m uvicorn api.api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 2. フロントエンド（Next.js）

```powershell
cd demo-web
copy .env.example .env.local
npm run dev
```

→ http://localhost:3000/demo/opening

### 3. テスト

```powershell
py -m pytest tests/test_demo_api.py tests/test_recommendation_v3.py -v
```

## 新規 API エンドポイント

| メソッド | パス |
|---------|------|
| GET | `/health`（`neo4j` フィールド追加） |
| GET | `/api/demo/questions` |
| POST | `/api/demo/sessions` |
| GET | `/api/demo/sessions/{id}` |
| POST | `/api/demo/sessions/{id}/answers` |
| PATCH | `/api/demo/sessions/{id}/delegation` |
| GET | `/api/demo/sessions/{id}/graph-path` |
| POST | `/api/demo/sessions/{id}/events` |
| GET | `/api/demo/fallback/recommend` |

## Phase 1 への引き継ぎ

- `demo-web`: SCR-02 Questions 画面の実装
- Supabase: 環境変数設定後に `session_store.py` を DB 実装に差し替え
- `/recommend`: `session_id` + プロファイル連携の拡張
