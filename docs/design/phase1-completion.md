# Phase 1 完了チェックリスト

> **完了日**: 2026-05-26

## デモフロー（MVP）

```
Opening → Quick Questions (5問) → AI Delegation → Recommendation
```

※ SCR-04 KG Visualization は Phase 2 で Delegation と Recommend の間に挿入

## 実装内容

| 画面 | パス | 状態 |
|------|------|------|
| SCR-01 Opening | `/demo/opening` | ✅ |
| SCR-02 Questions | `/demo/questions` | ✅ |
| SCR-03 Delegation | `/demo/delegation` | ✅ |
| SCR-05 Recommend | `/demo/recommend` | ✅ 簡易版 |

| API | 状態 |
|-----|------|
| `POST /api/demo/sessions/{id}/recommend` | ✅ |
| Delegation 連動表示 | ✅ |
| fallback バナー | ✅ |
| Zustand persist | ✅ |

## 起動

```powershell
# API
py -m uvicorn api.api_server:app --host 0.0.0.0 --port 8000 --reload

# FE
cd demo-web && npm run dev
```

## テスト

```powershell
py -m pytest tests/ -v
```
