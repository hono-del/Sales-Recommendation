# モック改善実装レポート

## 社内レビューフィードバック対応

### 実施日: 2026年5月29日

## 修正内容サマリー

### 1. Questionの変更（車に関係ない価値観判定の質問に変更）

**変更前**: 車に特化した4-7問の質問
**変更後**: 生活者の価値観を判定する5問

#### 新しい質問内容

1. **q1_decision_style**: 大きな買い物を決めるとき、あなたに近いのは？
   - たくさん比較して、最良の選択をしたい
   - 必要な条件が揃えば、そこで決める
   - 専門家の評価やランキングを重視する
   - 家族や友人の意見を聞いて決める
   - 第一印象や直感を大切にする

2. **q2_information**: 新しいことを始めるとき、どう情報を集めますか？
   - 詳しく調べて、比較検討する
   - 要点をまとめた情報を見る
   - 専門家のレビューや評価を参考にする
   - 周りの人の経験談を聞く
   - まず試してみてから判断する

3. **q3_priority**: 日々の生活で、最も大切にしていることは？
   - 安全・安心
   - 効率・合理性
   - 家族との時間
   - 自己成長・学び
   - 楽しさ・充実感

4. **q4_change**: 変化や新しいことに対して、あなたは？
   - 慎重に検討してから取り入れる
   - 必要性を感じたら取り入れる
   - 評判が良ければ試してみる
   - 信頼できる人に相談してから決める
   - 積極的に新しいことを試したい

5. **q5_time_usage**: 休日や自由な時間の過ごし方は？
   - 計画を立てて、効率よく過ごす
   - やることと休むことのバランスを取る
   - 家族と一緒に過ごす
   - 学びや自己成長の時間にする
   - リラックスや趣味を楽しむ

### 2. 画面フローの変更

**変更前**: Question → Delegation → Graph → Recommend → Dealer
**変更後**: Question → Delegation → **統合Recommend画面**（3セクション構成）→ Dealer

#### 統合Recommend画面の構成

1. **あなたへのおすすめ車種** + Decision Styleに合わせた情報提示
   - 推薦車種カード（3台）
   - Decision Style別の説明スタイル
   - 除外理由の表示

2. **営業トーク案**（新規）
   - お客様のご要望の確認
   - 車種の強み
   - 実際の使用イメージ
   - 次のステップのご提案

3. **なぜこの提案か？**（思考プロセス）
   - グラフビジュアライゼーション統合
   - 価値観 → KG Needs → 機能 → 車種の流れ

## 変更ファイル一覧

### 設定ファイル
- `config/questions.json` - 5問の新しい質問
- `config/score-weights.json` - 新しい質問IDに対応
- `config/need-mapping.json` - 新しい質問IDに対応
- `config/decision-style-weights.json` - 新しい質問IDに対応

### フロントエンド
- `demo-web/src/components/demo/DelegationClient.tsx` - 遷移先を `/demo/recommend` に変更
- `demo-web/src/components/demo/RecommendClient.tsx` - 3セクション統合
- `demo-web/src/components/demo/SalesTalkSection.tsx` - 営業トーク案コンポーネント（新規）
- `demo-web/src/components/demo/GraphClient.tsx` - 質問数チェック（4→5）
- `demo-web/src/lib/decision-style-calculator.ts` - applyGuards関数更新
- `demo-web/src/config/decision-style-weights.json` - 新しい質問IDに対応

## テスト手順

1. **サーバー起動**
   ```powershell
   cd "C:\Users\a01380\OneDrive - CMC Corporation\デスクトップ\次世代商談"
   .\start-demo.ps1
   ```

2. **動作確認**
   - 5問の質問が表示されること
   - 質問内容が車に関係ない価値観判定になっていること
   - Delegation画面の後、統合Recommend画面に遷移すること
   - Recommend画面で以下が表示されること：
     - おすすめ車種
     - 営業トーク案
     - 思考プロセス（グラフ）

3. **Decision Style判定**
   - 各質問の回答に応じて、適切なDecision Styleが判定されること
   - Maximizer, Satisficer, Authority-driven, Delegator, Intuitive のいずれかが判定されること

## 次のステップ

1. 実際のユーザーテストで5問の質問内容を検証
2. 営業トーク案の内容を実際の営業担当者からフィードバックをもらい改善
3. 思考プロセスの可視化をさらにブラッシュアップ

## 技術的メモ

- 質問数を動的に処理しているため、将来的に質問を追加・削除しやすい設計
- Decision Style判定ロジックは重み付けベースで、調整が容易
- 営業トーク案は推薦理由から自動生成されるが、カスタマイズ可能
