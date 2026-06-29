# Vercel KV セットアップガイド

## 問題

現在、サービスフィードバックは `sessions.json` ファイルに保存されています。
Vercel環境では：
- ファイルシステムが読み取り専用
- デプロイごとにデータがリセット
- **フィードバックが保存されない**

## 解決策: Vercel KV（Redis）

Vercel KV を使うと、永続化されたストレージでフィードバックを保存できます。

---

## 1. Vercel KV をセットアップ

### Vercelダッシュボードで:

1. https://vercel.com/hono-2482s-projects/sales-recommendation にアクセス
2. **Storage** タブを開く
3. **Create Database** → **KV** を選択
4. データベース名（例: `sales-recommendation-kv`）を入力
5. **Create** をクリック

### 環境変数の自動設定

Vercel は自動的に以下の環境変数を設定します：
```
KV_REST_API_URL=https://xxx.kv.vercel-storage.com
KV_REST_API_TOKEN=eyJ...
```

---

## 2. コードの変更（すでに完了）

以下のファイルがすでに対応済みです：

### `api/demo/session_store_vercel.py`
- Vercel KV に対応したセッションストア
- `KV_REST_API_URL` があれば自動的に KV を使用
- なければローカルの `sessions.json` を使用

### `api/demo/session_store.py`
- `get_session_store()` が環境変数を検知して自動切り替え

### `api/demo/router.py`
- `/api/demo/feedback-logs` エンドポイントを追加
- Vercel環境でもフィードバック履歴を取得可能

### `demo-web/src/app/demo/feedback-logs/page.tsx`
- フィードバックログ表示ページ

---

## 3. 動作確認

### ローカル環境

```powershell
# 現在のまま動作（sessions.json を使用）
.\start-demo.ps1
```

### Vercel環境

1. **Vercel KV 作成後、自動的に再デプロイ**
2. https://sales-recommendation.vercel.app/demo/service/recommend でフィードバック保存
3. https://sales-recommendation.vercel.app/demo/feedback-logs で履歴確認

---

## 4. API エンドポイント

### フィードバック保存（既存）
```
POST /api/demo/sessions/{session_id}/service-feedback
```

### フィードバックログ取得（新規）
```
GET /api/demo/feedback-logs
```

レスポンス例：
```json
{
  "total_sessions": 150,
  "sessions_with_feedback": 23,
  "feedbacks": [
    {
      "session_id": "abc123...",
      "created_at": "2026-06-29T...",
      "updated_at": "2026-06-29T...",
      "feedback_count": 3,
      "feedbacks": [
        {
          "service_id": "S-22",
          "feedback_value": "want_details",
          "timestamp": "2026-06-29T..."
        }
      ]
    }
  ]
}
```

---

## 5. トラブルシューティング

### Vercel でフィードバックが保存されない

**確認項目:**
1. Vercel KV が作成されているか → Storage タブで確認
2. 環境変数が設定されているか → Settings → Environment Variables
3. 再デプロイしたか → Deployments → Redeploy

**ログ確認:**
```
Vercel Dashboard → Functions タブ → ログを確認
[SessionStore] Using Vercel KV for persistence
```

### ローカルで動作しない

**確認項目:**
1. `data/demo/sessions.json` が存在するか
2. APIサーバーが起動しているか（port 8000）

---

## 6. データ移行（オプション）

既存の `sessions.json` から Vercel KV にデータを移行する場合：

```python
# api/demo/migrate_to_kv.py
import json
import os
import requests

KV_URL = os.getenv("KV_REST_API_URL")
KV_TOKEN = os.getenv("KV_REST_API_TOKEN")

with open("data/demo/sessions.json") as f:
    sessions = json.load(f)

for sid, session in sessions.items():
    requests.post(
        f"{KV_URL}/set/session:{sid}",
        headers={"Authorization": f"Bearer {KV_TOKEN}"},
        json={"value": json.dumps(session)},
    )
    print(f"Migrated {sid}")
```

---

## まとめ

✅ **Vercel KV セットアップ完了後:**
- フィードバックが永続化される
- デプロイごとにリセットされない
- `/demo/feedback-logs` でログ履歴が確認できる

✅ **ローカル環境:**
- 引き続き `sessions.json` を使用
- 既存の動作に影響なし

次のステップ: Vercel ダッシュボードで KV を作成 → 自動再デプロイ → 動作確認
