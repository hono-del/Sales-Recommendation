# Supabase セットアップガイド

## 問題

現在、サービスフィードバックは `sessions.json` ファイルに保存されています。
Vercel環境では：
- ファイルシステムが読み取り専用
- デプロイごとにデータがリセット
- **フィードバックが保存されない**

## 解決策: Supabase（PostgreSQL）

Supabase を使うと、永続化されたデータベースでフィードバックを保存できます。

---

## 1. Supabase プロジェクトを作成

### Supabase ダッシュボードで:

1. https://supabase.com/dashboard にアクセス
2. **New Project** をクリック
3. プロジェクト名: `sales-recommendation`
4. Database Password を設定（メモしておく）
5. Region: `Northeast Asia (Tokyo)` を推奨
6. **Create new project** をクリック

---

## 2. テーブルを作成

### SQL エディタで実行:

1. 左メニュー → **SQL Editor**
2. **New query** をクリック
3. 以下のSQLを実行:

```sql
-- セッションデータ保存用テーブル
CREATE TABLE IF NOT EXISTS demo_sessions (
  session_id TEXT PRIMARY KEY,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 更新日時インデックス（最新順取得を高速化）
CREATE INDEX IF NOT EXISTS idx_demo_sessions_updated_at 
ON demo_sessions(updated_at DESC);

-- フィードバック検索用インデックス
CREATE INDEX IF NOT EXISTS idx_demo_sessions_feedback 
ON demo_sessions USING GIN ((data -> 'service_feedbacks'));
```

4. **Run** をクリック

---

## 3. API キーを取得

### Settings → API で:

1. **Project URL** をコピー（例: `https://xxxxx.supabase.co`）
2. **anon public** キーをコピー（公開用、不要）
3. **service_role** キーをコピー（**重要：秘密情報**）

---

## 4. Vercel に環境変数を設定

### Vercel ダッシュボードで:

1. https://vercel.com/hono-2482s-projects/sales-recommendation/settings/environment-variables
2. 以下の環境変数を追加:

| Name | Value | Environment |
|------|-------|-------------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | Production, Preview, Development |
| `SUPABASE_SERVICE_KEY` | `eyJ...` (service_role key) | Production, Preview, Development |

3. **Save** をクリック

---

## 5. 再デプロイ

環境変数を追加後、Vercel が自動的に再デプロイします。
または手動で：

1. https://vercel.com/hono-2482s-projects/sales-recommendation/deployments
2. 最新デプロイの **...** → **Redeploy**

---

## 6. 動作確認

### フィードバック保存

1. https://sales-recommendation.vercel.app/demo/service/recommend
2. 質問に回答 → おすすめ画面
3. フィードバックボタンをクリック
4. 「FBを保存」をクリック

### ログ確認

**Webページで確認:**
https://sales-recommendation.vercel.app/demo/feedback-logs

**Supabase で直接確認:**
1. Supabase Dashboard → **Table Editor**
2. `demo_sessions` テーブルを開く
3. `data` カラムに `service_feedbacks` が含まれているか確認

---

## 7. ローカル環境

**変更なし** — 引き続き `sessions.json` を使用します。

```powershell
.\start-demo.ps1
```

Supabase に接続したい場合は、`.env` に追加:

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

---

## API エンドポイント

### フィードバック保存（既存）
```
POST /api/demo/sessions/{session_id}/service-feedback
```

### フィードバックログ取得（新規）
```
GET /api/demo/feedback-logs
```

---

## トラブルシューティング

### Vercel でフィードバックが保存されない

**確認項目:**
1. Supabase テーブルが作成されているか → Table Editor で確認
2. 環境変数が設定されているか → Settings → Environment Variables
3. 再デプロイしたか → Deployments → Redeploy

**ログ確認:**
```
Vercel Dashboard → Functions タブ → ログを確認
[SessionStore] Using Supabase for persistence
```

### Supabase 接続エラー

**確認項目:**
1. `SUPABASE_URL` が正しいか（`https://` 含む）
2. `SUPABASE_SERVICE_KEY` が `service_role` キーか（`anon` ではない）
3. Supabase プロジェクトが起動しているか

---

## データ移行（オプション）

既存の `sessions.json` から Supabase にデータを移行する場合：

```python
# api/demo/migrate_to_supabase.py
import json
import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

with open("data/demo/sessions.json") as f:
    sessions = json.load(f)

for sid, session in sessions.items():
    requests.post(
        f"{SUPABASE_URL}/rest/v1/demo_sessions",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        json={
            "session_id": sid,
            "data": session,
        },
    )
    print(f"Migrated {sid}")
```

---

## セキュリティ

⚠️ **重要:**
- `SUPABASE_SERVICE_KEY` は絶対に公開しないでください
- GitHub にコミットしないでください（`.env` は `.gitignore` に含める）
- フロントエンド（Next.js）では使用しないでください

---

## まとめ

✅ **Supabase セットアップ完了後:**
- フィードバックが永続化される
- デプロイごとにリセットされない
- `/demo/feedback-logs` でログ履歴が確認できる
- PostgreSQL の強力なクエリ機能を活用できる

✅ **ローカル環境:**
- 引き続き `sessions.json` を使用
- 既存の動作に影響なし

次のステップ: Supabase プロジェクト作成 → テーブル作成 → Vercel 環境変数設定 → 動作確認
