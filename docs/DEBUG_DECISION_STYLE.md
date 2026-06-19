# DecisionStyle 表示切り替えデバッグガイド

## 確認手順

### 1. ブラウザキャッシュをクリア

**重要**: Vercelのデプロイ後は必ずキャッシュをクリアしてください

- **Windows/Linux**: `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`
- または: ブラウザ設定 → キャッシュとCookieをクリア

### 2. コンソールログを開く

1. ブラウザで F12 キーを押す
2. 「Console」タブを選択
3. ログをクリア（🚫アイコン）

### 3. 新しいセッションで質問に回答

1. サービスレコメンドを最初から開始
2. 質問1で異なる選択肢を選ぶ
3. コンソールで以下のログを確認：

```
✓ 正常な場合:
[ServiceQuestions] Setting DecisionStyle from Q1: {name: "Intuitive", label: "直感型", ...}
[ServiceQuestions] Saved DecisionStyle to Zustand store

✗ 異常な場合:
回答送信エラー: ...
または、上記のログが表示されない
```

4. 質問2〜4に回答して「レコメンドを見る」をクリック

5. おすすめサービス画面で以下のログを確認：

```
✓ 正常な場合:
[ServiceRecommend] DecisionStyle from store: {name: "Intuitive", ...}
[ServiceRecommend] getDisplayConfig - decisionStyle: {name: "Intuitive", ...}
[ServiceRecommend] styleName: Intuitive
[ServiceRecommend] displayConfig: {
  title: "あなたにぴったりのサービス（直感型）",
  layout: "visual",
  ...
}

✗ 異常な場合:
[ServiceRecommend] DecisionStyle from store: null
または、上記のログが表示されない
```

### 4. 画面表示を確認

各DecisionStyleで期待される表示：

| DecisionStyle | タイトル | 特徴 |
|--------------|---------|------|
| Intuitive | あなたにぴったりのサービス（直感型） | シンプルな表示 |
| Authority-driven | 専門家が推奨するサービス（権威依存型） | 青いバナー「実績と評価に基づいた...」 |
| Satisficer | あなたに最適なサービス（十分型） | 1位が金色の枠で大きく表示 |
| Maximizer | あなたにおすすめのサービス（徹底比較型） | 詳細スコア表示 |
| Delegator | 多くの方に選ばれているサービス（委任型） | 緑のバナー「多くのお客様に...」 |

## よくある問題と解決方法

### 問題1: タイトルが変わらない

**原因**: ブラウザキャッシュ、またはVercelのデプロイが未完了

**解決方法**:
1. Vercelダッシュボードで最新デプロイのステータスを確認
2. 「Ready」になっていることを確認
3. ブラウザキャッシュをクリア（Ctrl + Shift + R）
4. 新しいシークレットウィンドウで開く

### 問題2: コンソールログが表示されない

**原因**: 本番ビルドではコンソールログが削除される可能性

**解決方法**:
1. ローカル開発環境で確認:
   ```powershell
   cd demo-web
   npm run dev
   ```
2. http://localhost:3000 でテスト

### 問題3: DecisionStyleが null

**原因**: Zustandストアへの保存が失敗している

**解決方法**:
1. React DevTools をインストール
2. Components タブを開く
3. `ServiceQuestionsClient` を選択
4. hooks → useDemoStore → decisionStyle の値を確認

### 問題4: API エラー

**原因**: バックエンド（Render）の再起動が必要

**解決方法**:
1. Renderダッシュボードを開く
2. サービスの状態を確認
3. 必要に応じて手動再起動

## 直接確認できる項目

### URL パラメータで確認

現在のセッションID:
```
https://sales-recommendation.vercel.app/demo/service/recommend
→ ブラウザのセッションストレージに保存
```

### React DevTools で確認

1. React DevTools をインストール
2. Components タブ
3. ServiceRecommendClient を選択
4. State → decisionStyle を確認

### Network タブで確認

1. F12 → Network タブ
2. `/api/demo/sessions/{session_id}` リクエストを探す
3. Response に `decision_style` が含まれるか確認

## 期待される動作フロー

```
質問1回答
↓
[ServiceQuestionsClient]
- DecisionStyleを判定（choice.key → styleName）
- ローカルステートに保存
- Zustandストアに保存 ← 重要！
↓
質問2〜4回答
↓
「レコメンドを見る」クリック
↓
[ServiceRecommendClient]
- Zustandストアから取得 ← ここで取れない場合はバグ
- getDisplayConfig() を呼び出し
- layout と showDetailedScores を決定
↓
[ServiceOfferingSection]
- layout に応じて表示を切り替え
```

## 最終確認

すべて試しても解決しない場合:

1. ローカルで動作確認:
   ```powershell
   cd "C:\Users\a01380\OneDrive - CMC Corporation\デスクトップ\次世代商談"
   .\start.ps1
   ```

2. コンソールログをスクリーンショットで共有
3. React DevTools のスクリーンショットで共有
