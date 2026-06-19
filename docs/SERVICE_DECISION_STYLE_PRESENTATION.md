# サービスレコメンド - Decisionスタイル別表示方法

**作成日**: 2026-06-18  
**目的**: サービスレコメンドにおける各Decisionスタイル別の表示方法を定義

---

## 実装状況

### 質問1でDecisionStyle判定

質問1「大きな買い物を決めるとき、あなたに近いのは？」の回答から直接マッピング：

| 回答選択肢 | answer_key | DecisionStyle | 日本語ラベル |
|-----------|-----------|---------------|-------------|
| 第一印象や直感を大切にする | intuition | Intuitive | 直感型 |
| 専門家の評価やランキングを重視する | trust_authority | Authority-driven | 権威依存型 |
| たくさん比較して、最良の選択をしたい | compare_thoroughly | Maximizer | 徹底比較型 |
| 家族や友人の意見を聞いて決める | ask_others | Delegator | 委任型 |
| 必要な条件が揃えば、そこで決める | good_enough | Satisficer | 十分型 |

---

## スタイル別表示設計

### 1. Maximizer（徹底比較型）

**特徴**: 多数比較・後悔回避・詳細分析

**表示方法**:
- タイトル: 「あなたにおすすめのサービス（徹底比較型）」
- サブタイトル: 「全てのサービスを詳しく比較し、最適な選択ができます」
- **表示件数**: 全サービス
- **レイアウト**: `comparison`
- **詳細スコア表示**: ON
  - ニーズマッチ率
  - 負荷対応率
  - 価値観一致率

**UI要素**:
```typescript
layout: "comparison"
showDetailedScores: true
maxServices: services.length  // 全件表示
```

**表示例**:
- 各サービスカードに詳細スコア内訳を表示
- すべてのサービスを並列に比較可能
- 参照した知識セクションを詳細に表示

---

### 2. Satisficer（十分型）⭐

**特徴**: 基準を満たせば決定・比較数を抑える

**表示方法**:
- タイトル: 「あなたに最適なサービス（十分型）」
- サブタイトル: 「必要な条件を満たした最適なサービスをご提案します」
- **表示件数**: 上位5件（1位は特別扱い）
- **レイアウト**: `hero`
- **詳細スコア表示**: OFF

**UI要素**:
```typescript
layout: "hero"
showDetailedScores: false
maxServices: 5
```

**特別表示（1位のみ）**:
- 金色の枠で強調
- 「⭐ あなたに最適な1つ」バッジ
- 大きなサイズ（p-8, text-2xl）
- 「✓ このサービスがあなたに最適な理由」セクション:
  - 必要な条件を満たしています
  - あなたの価値観に合致しています
  - 過不足のないバランスの良い選択です

**2位以降**:
- `<details>` 折りたたみで控えめに表示
- デフォルトで閉じている
- 「参考：他の選択肢も見る（X件）」

---

### 3. Authority-driven（権威依存型）

**特徴**: 専門家・実績・評価を信頼

**表示方法**:
- タイトル: 「専門家が推奨するサービス（権威依存型）」
- サブタイトル: 「実績と評価に基づいた信頼性の高いサービスです」
- **表示件数**: 全サービス
- **レイアウト**: `authority`
- **詳細スコア表示**: OFF

**UI要素**:
```typescript
layout: "authority"
showDetailedScores: false
maxServices: services.length
```

**特別表示**:
- ページ上部に青いバナー表示:
  - 「✓ 実績と評価に基づいた信頼性の高いサービスをご提案しています」
- 各サービスの信頼性指標を強調

---

### 4. Delegator（委任型）

**特徴**: 他者に評価・決定を任せる

**表示方法**:
- タイトル: 「多くの方に選ばれているサービス（委任型）」
- サブタイトル: 「あなたと同じ条件の方に人気のサービスです」
- **表示件数**: 上位7件
- **レイアウト**: `popular`
- **詳細スコア表示**: OFF

**UI要素**:
```typescript
layout: "popular"
showDetailedScores: false
maxServices: 7
```

**特別表示**:
- ページ上部に緑のバナー表示:
  - 「👥 多くのお客様に選ばれているサービスです」
- 上位3件に「👥 人気 No.X」バッジを追加

---

### 5. Intuitive（直感型）

**特徴**: 感触・体験重視・ビジュアル優先

**表示方法**:
- タイトル: 「あなたにぴったりのサービス（直感型）」
- サブタイトル: 「体験価値を重視したサービスをご提案します」
- **表示件数**: 全サービス
- **レイアウト**: `visual`
- **詳細スコア表示**: OFF

**UI要素**:
```typescript
layout: "visual"
showDetailedScores: false
maxServices: services.length
```

**特別表示**:
- 詳細な技術説明を最小限に
- 推薦理由の詳細テキストを非表示
- シンプルで直感的なカードデザイン

---

### 6. Impulsive（即決型）

**特徴**: 即決・キャンペーン敏感・緊急性

**表示方法**:
- タイトル: 「今すぐ始められるサービス（即決型）」
- サブタイトル: 「期間限定の特別なご提案です」
- **表示件数**: 全サービス
- **レイアウト**: `urgent`
- **詳細スコア表示**: OFF

**UI要素**:
```typescript
layout: "urgent"
showDetailedScores: false
maxServices: services.length
```

**特別表示**:
- ページ上部に赤いバナー表示:
  - 「⚡ 今だけの特別なご提案です」
- 1位に「⚡ 今だけ」アニメーション付きバッジ
- アクションボタンを金色に変更
- ボタンテキスト: 「今すぐ相談」

---

## 実装ファイル

### ServiceQuestionsClient.tsx
- 質問1の回答時にDecisionStyleを判定
- Zustandストアに保存

### ServiceRecommendClient.tsx
- Zustandストアからdecision Styleを取得
- `getDisplayConfig()` でスタイル別の設定を返す
- `layout` と `showDetailedScores` をServiceOfferingSectionに渡す

### ServiceOfferingSection.tsx
- `layout` propに応じて表示を切り替え
- `layout === "hero"` で Satisficer 専用レイアウト
- その他のレイアウトでバナー表示やバッジ追加

---

## デバッグ方法

ブラウザのコンソール（F12 → Console）で以下のログを確認：

```javascript
[ServiceQuestions] Setting DecisionStyle from Q1: {name: "Intuitive", ...}
[ServiceQuestions] Saved DecisionStyle to Zustand store
[ServiceRecommend] DecisionStyle from store: {name: "Intuitive", ...}
[ServiceRecommend] styleName: Intuitive
[ServiceRecommend] getDisplayConfig - decisionStyle: {...}
[ServiceRecommend] displayConfig: {layout: "visual", ...}
```

---

## トラブルシューティング

### 表示が変わらない場合

1. **ブラウザキャッシュをクリア**
   - Ctrl + Shift + R（Windows）
   - Cmd + Shift + R（Mac）

2. **コンソールログを確認**
   - F12 → Console タブ
   - `[ServiceRecommend] styleName:` の値を確認
   - `null` や `undefined` の場合、DecisionStyleが取得できていない

3. **Zustandストアを確認**
   - React DevTools → Components → useDemoStore
   - `decisionStyle` の値を確認

4. **質問1を再度回答**
   - 新しいセッションで質問1から回答
   - コンソールログで保存を確認

---

## 今後の拡張案

### Phase 2
- Authority-driven: 専門家レビュー引用
- Delegator: 類似ユーザーの選択率表示
- Impulsive: カウントダウンタイマー

### Phase 3
- A/Bテスト機能
- スタイル別のコンバージョン率測定
- ユーザーフィードバック収集

---

## 参考

- 車種レコメンド版: `docs/DECISION_STYLE_PRESENTATION.md`
- サービスロジック: `docs/SERVICE_RECOMMENDATION_LOGIC.md`
