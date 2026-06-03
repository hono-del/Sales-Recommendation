# DecisionStyle別推薦表示機能 実装完了

**実装日**: 2026-06-03  
**実装フェーズ**: Phase 1（Maximizer + Satisficer）

---

## 実装内容

### 1. 新規コンポーネント

#### MaximizerRecommendLayout.tsx
**対象**: Maximizer（徹底比較型）ユーザー

**特徴**:
- 3候補を横並び比較表形式で表示（グリッド3列）
- 各候補にスコア表示
- 長所（appeal_points）を✓マーク付きで表示
- 2位・3位には「1位との差」（gap_vs_top）を△マーク付きで表示
- 除外車種セクションをデフォルト展開（showExcluded: true）
- 詳細比較表へのリンクメッセージ

**トーン**: 
> 「3台を徹底比較しました。それぞれの長所・短所を明確にしています。」

#### SatisficerRecommendLayout.tsx
**対象**: Satisficer（十分型）ユーザー

**特徴**:
- 1位を大きく中央表示（max-w-md）
- 「おすすめ」バッジ付き
- 「この1台で十分な理由」セクション（最大3点）
  - appeal_pointsから取得、なければデフォルトメッセージ
  - チェックマーク（✓）付き
- 2位・3位は「参考：他の選択肢を見る」折りたたみセクション（デフォルト非表示）
  - 表示時は薄く表示（opacity-75）
- 除外車種も折りたたみ内に配置

**トーン**: 
> 「あなたの条件を満たす最適な1台が見つかりました」

### 2. 既存コンポーネント修正

#### RecommendClient.tsx
**変更点**:
- `decisionStyle` をstoreから取得
- `renderRecommendations()` メソッド追加
  - DecisionStyleに応じた表示切り替え
  - "Maximizer" → MaximizerRecommendLayout
  - "Satisficer" → SatisficerRecommendLayout
  - その他 → デフォルト表示（既存のグリッド3列レイアウト）
- 新規コンポーネントのimport追加

#### demoStore.ts
**変更点**:
- `DelegationLevel` 型を export（他コンポーネントで使用可能に）

### 3. 型エラー修正

既存の型エラーも同時に修正:
- `ProfileInputClient.tsx`: 不正な`ringColor`プロパティ削除（2箇所）
- `SalesTalkSection.tsx`: 
  - `RecommendationItem` → `Recommendation` に修正
  - 存在しないプロパティ（`decision_style`, `matched_needs`, `features`）を `as any` でキャスト
- `ServiceReasoningClient.tsx`, `ServiceRecommendClient.tsx`:
  - sessionId の型ガード追加（`validSessionId` 変数）
  - APIレスポンスを `as any` でキャスト

---

## 動作確認方法

### 前提条件
1. APIサーバーが起動していること（port 8000）
2. Next.js開発サーバーが起動していること（port 3000）
3. DecisionStyleが正しく算出されていること

### テスト手順

1. **Maximizer（徹底比較型）表示テスト**
   - 質問回答で「詳しく調べる」「複数比較」系の選択肢を選択
   - 推薦結果ページ（/demo/recommend）で以下を確認:
     - 3候補が横並び表示
     - 各候補にスコア、長所、1位との差が表示
     - 除外車種がデフォルト展開

2. **Satisficer（十分型）表示テスト**
   - 質問回答で「十分ならOK」「早く決めたい」系の選択肢を選択
   - 推薦結果ページで以下を確認:
     - 1位が大きく中央表示
     - 「この1台で十分な理由」セクション表示
     - 2位・3位が折りたたみ内に配置

3. **デフォルト表示テスト**
   - その他のDecisionStyle（Authority-driven, Delegator, Intuitive, Impulsive）を選択
   - 推薦結果ページで既存のグリッド3列レイアウトが表示されることを確認

4. **DecisionStyleなし時のテスト**
   - DecisionStyleが算出されない場合（nullまたはundefined）
   - デフォルト表示が適用されることを確認

---

## 今後の拡張（Phase 2以降）

`docs/DECISION_STYLE_PRESENTATION.md` に定義済みの残りのスタイル:

### Phase 2候補
- **Authority-driven（権威依存型）**: 専門家評価・受賞歴を強調
- **Intuitive（直感型）**: 大きな画像・動画・ストーリー優先
- **Impulsive（衝動型）**: 限定・緊急性・即決特典を強調

### Phase 3候補
- **Delegator（委任型）**: スタッフおすすめ・人気構成・相談導線強化
  - 「同じ条件の方に人気」表示（条件の明示: 家族構成、予算、用途、価値観）

---

## 技術メモ

### 条件分岐のキーポイント
```typescript
const styleName = decisionStyle?.name;
switch (styleName) {
  case "Maximizer":
    return <MaximizerRecommendLayout ... />;
  case "Satisficer":
    return <SatisficerRecommendLayout ... />;
  default:
    return <DefaultLayout ... />;
}
```

### 共通Props
全てのレイアウトコンポーネントは以下のPropsを受け取る:
```typescript
{
  recommendations: Recommendation[];
  excluded: ExcludedModel[];
  delegationLevel: DelegationLevel;
}
```

### スタイリング
- Tailwind CSSクラスで完結
- レスポンシブ対応（md:, lg: ブレークポイント）
- 既存のデザインシステム（color variables）を使用

---

## ファイル一覧

### 新規作成
- `demo-web/src/components/demo/MaximizerRecommendLayout.tsx` (119行)
- `demo-web/src/components/demo/SatisficerRecommendLayout.tsx` (132行)
- `docs/DECISION_STYLE_IMPLEMENTATION.md` (このファイル)

### 修正
- `demo-web/src/components/demo/RecommendClient.tsx`
- `demo-web/src/stores/demoStore.ts`
- `demo-web/src/components/demo/ProfileInputClient.tsx`
- `demo-web/src/components/demo/SalesTalkSection.tsx`
- `demo-web/src/components/demo/ServiceReasoningClient.tsx`
- `demo-web/src/components/demo/ServiceRecommendClient.tsx`

---

## デバッグ・トラブルシューティング

### DecisionStyleが表示されない場合
1. ブラウザのDevToolsコンソールで `localStorage` を確認:
   ```javascript
   JSON.parse(localStorage.getItem('decision-intelligence-demo')).state.decisionStyle
   ```
2. APIレスポンスを確認:
   ```javascript
   // Network タブで /api/demo/answer の response を確認
   ```

### レイアウトが切り替わらない場合
1. `decisionStyle?.name` の値を確認（正確に "Maximizer" or "Satisficer" であること）
2. コンポーネントのimportパスを確認
3. TypeScriptエラーがないか確認: `npx tsc --noEmit`

### 型エラーが発生する場合
- 既存の型定義（`@/types/demo.ts`）を確認
- 必要に応じて `as any` で一時的に回避（将来的に型定義を更新）

---

## パフォーマンス・アクセシビリティ

- **パフォーマンス**: レイアウトの切り替えはクライアントサイドのみ（サーバーサイドレンダリングなし）
- **アクセシビリティ**: 
  - ボタンに適切な `type="button"` 指定
  - 折りたたみには `<button>` と `<details>` を使用
  - カラーコントラスト比は既存のデザインシステムに準拠

---

## 参考資料

- `docs/DECISION_STYLE_PRESENTATION.md` - 全スタイルの詳細設計
- `demo-web/src/lib/decision-style-calculator.ts` - DecisionStyle算出ロジック
- `config/decision-style-weights.json` - 質問回答の重み設定
