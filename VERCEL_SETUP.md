# Vercel デプロイ設定ガイド

## 問題: 404 NOT_FOUND エラー

現在、`https://sales-recommendation.vercel.app` で 404 エラーが発生しています。

## 原因

Vercel が **プロジェクトルート** をビルドしようとしているが、実際の Next.js アプリは `demo-web/` サブディレクトリにあるため。

## 解決方法

### オプション1: Vercel ダッシュボードで設定（推奨）

1. **Vercel ダッシュボードにアクセス**
   - https://vercel.com/hono-2482s-projects/sales-recommendation/settings

2. **General タブを開く**

3. **"Root Directory" セクション を見つける**
   - 現在: `./` (プロジェクトルート) ← 問題の原因
   - 変更: `demo-web` ← これに変更する

4. **"Edit" ボタンをクリック**

5. **Root Directory を `demo-web` に変更**
   - 入力欄に `demo-web` と入力
   - "Include source files outside of the Root Directory in the Build Step" にチェックを入れる

6. **"Save" をクリック**

7. **Deployments タブに戻る**

8. **"Redeploy" をクリック**
   - 最新のデプロイを選択
   - "Redeploy" ボタンをクリック
   - 確認ダイアログで "Redeploy" を再度クリック

9. **ビルド完了を待つ（2-3分）**

10. **https://sales-recommendation.vercel.app にアクセスして確認**

### オプション2: Vercel CLI で設定

```powershell
# Vercel にログイン
vercel login

# プロジェクトディレクトリに移動
cd "C:\Users\a01380\OneDrive - CMC Corporation\デスクトップ\次世代商談"

# プロジェクトをリンク
vercel link --project sales-recommendation

# demo-web ディレクトリからデプロイ
cd demo-web
vercel --prod
```

### オプション3: プロジェクト構造を変更（非推奨）

demo-web の内容をプロジェクトルートに移動する方法もありますが、既存の構造を壊すため推奨しません。

## 確認方法

デプロイ成功後、以下を確認：

1. **ルートURL** (`https://sales-recommendation.vercel.app/`)
   - → `/demo/opening` にリダイレクトされる

2. **Opening 画面** (`https://sales-recommendation.vercel.app/demo/opening`)
   - タイトル: "なぜ、その車なのか？"
   - サブタイトル: "Knowledge Graph で可視化する意思決定支援"
   - 「体験を始める」ボタン

3. **スタイル確認**
   - Tailwind CSS が正しく適用されている
   - フォント、色、レイアウトが正常

## トラブルシューティング

### ビルドエラーが出る

**エラー**: `Cannot find module 'next'`
- **原因**: install command が正しくない
- **解決**: Settings → General → Install Command を `npm install --prefix demo-web` に変更

**エラー**: `Build command failed`
- **原因**: build command が正しくない
- **解決**: Settings → General → Build Command を `cd demo-web && npm run build` に変更

### ページが真っ白

**原因**: CSS が読み込まれていない
- **解決**: ハードリフレッシュ（Ctrl+Shift+R）してキャッシュクリア

### まだ 404 エラー

**原因**: 古いビルドがキャッシュされている
- **解決**: 
  1. Deployments → 最新デプロイの "..." メニュー → "Delete"
  2. "Redeploy" で新規デプロイ

## 現在の設定値（記録用）

| 項目 | 正しい値 |
|------|---------|
| Framework Preset | Next.js |
| Root Directory | `demo-web` |
| Build Command | `npm run build` (自動検出) |
| Output Directory | `.next` (自動検出) |
| Install Command | `npm install` (自動検出) |
| Node.js Version | 18.x または 20.x |

## 環境変数（後で追加）

API をデプロイした後で追加：

```
NEXT_PUBLIC_API_URL=https://your-api-url.com
```

## 参考リンク

- [Vercel Monorepo 設定](https://vercel.com/docs/monorepos)
- [Next.js デプロイガイド](https://nextjs.org/docs/deployment)
- [Root Directory 設定](https://vercel.com/docs/concepts/projects/overview#root-directory)
