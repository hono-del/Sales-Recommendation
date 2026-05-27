# Phase 3 完了チェックリスト — OEM ストーリー

> **完了日**: 2026-05-27

## 成果物

| WBS | 内容 | 状態 |
|-----|------|------|
| W3.1 | dealer-talk API（テンプレート） | ✅ |
| W3.2 | Dealer Support 画面完全版 | ✅ |
| W3.3 | AXIS Closing 画面 | ✅ |
| W3.4 | オペレーターガイド | ✅（本ファイル含む） |
| W3.5 | 本番リハーサル手順 | ✅ |

## 画面実装

### SCR-06: Dealer Support

**実装内容**:
- KPI 3指標（マッチ度・推薦車種・顧客タイプ）
- 顧客インサイト（タイプ・シーン・不安・価値観）
- 提案トークスクリプト（テンプレート生成）
- 次のアクション（試乗・相談・AXIS 案内）

**API**: `POST /api/demo/sessions/{id}/dealer-talk`

### SCR-07: AXIS Closing

**実装内容**:
- 購入後ジャーニー（4ステップカード）
- AXIS 連携イメージ（メンテナンス・分析・次回購入）
- PoC 明示バナー
- リセット・やり直しボタン

## デモフロー（7画面・7分想定）

```
SCR-01 Opening (0:30)
  ↓ 体験を開始する
SCR-02 Questions (2:00)
  ↓ 5問完了
SCR-03 Delegation (0:30)
  ↓ 推薦理由を見る
SCR-04 Graph (1:30)
  ↓ おすすめを見る
SCR-05 Recommend (1:30)
  ↓ 販売店提案へ
SCR-06 Dealer (0:40)
  ↓ 購入後体験を見る
SCR-07 Closing (0:20)
  → もう一度体験する
```

## オペレーターガイド

### 起動手順

```powershell
# プロジェクトルートで実行
.\start-demo.ps1
```

または手動：

```powershell
# ターミナル1: API
cd "C:\Users\a01380\OneDrive - CMC Corporation\デスクトップ\次世代商談"
$env:NEO4J_PASSWORD="recommendation"
py -m uvicorn api.api_server:app --host 0.0.0.0 --port 8000

# ターミナル2: Next.js
cd demo-web
npm run dev
```

→ http://localhost:3000/demo/opening を Chrome / Edge で開く

### デモトーク台本（7分）

#### Opening（30秒）
> 「こちらは Decision Intelligence のコンセプトデモです。SDV 時代、選択肢が増えるほど、お客様は迷います。本システムは、選択肢を『増やす』のではなく『迷わない形に整理』し、なぜその提案かを説明できる状態を作ります。」

#### Questions（2分）
> 「まず5問の質問で、あなたの価値観を理解します。右側に、理解度が可視化されます。」
- Q1-5 を順に選択
- ProfileMap の変化を見せる

#### Delegation（30秒）
> 「AI との距離感を選べます。『ガイド型』では理由を詳しく、『オート型』では結論を優先して表示します。今回は『コパイロット型』でバランスよく進めます。」

#### Graph（1分30秒）
> 「ここが核心です。Knowledge Graph により、あなたの価値観・生活・不安が、どの機能・車種につながるかを可視化します。AI が勝手に決めているわけではなく、因果が見えます。」
- アニメーション完了まで待つ（スキップも可）
- Why Panel を指差しながら説明

#### Recommend（1分30秒）
> 「3候補を提案します。1位は VEZEL で 92%。『なぜ外した？』を押すと、除外理由も説明されます。迷いません。」

#### Dealer（40秒）
> 「販売店スタッフ向けに、顧客インサイトと提案トークを自動生成します。価値観・不安を踏まえた試乗提案など、次のアクションが明確になります。」

#### Closing（20秒）
> 「Decision Intelligence は『売って終わり』ではなく、購入後も AXIS で伴走します。メンテナンス・次回購入まで一気通貫です。本日はありがとうございました。」

### トラブルシューティング

| 問題 | 対処 |
|------|------|
| Graph が空 | Neo4j 未起動。Neo4j Desktop で "Recommendation" を Start |
| API エラー | `http://localhost:8000/health` で確認。port 8000 が使用中なら再起動 |
| Demo Mode バナー | Neo4j 停止時の fallback。完走は可能（KG は固定データ） |
| Recommend 0件 | API ログ確認。v3 オントロジー未構築なら `py graph_builder.py` |

### リセット方法

- 画面右上「最初からやり直す」
- または Closing 画面で「もう一度体験する」

## テスト

```powershell
py -m pytest tests/test_phase1_recommend.py tests/test_phase2_graph_path.py tests/test_demo_api.py -q
```

全 12 tests 通過確認済み。

## Phase 3 で追加した機能

| 機能 | Before | After |
|------|--------|-------|
| Dealer KPI | なし | マッチ度・車種・タイプの3指標 |
| Dealer デザイン | 単純2列 | アイコン・次のアクション・枠強調 |
| Closing ジャーニー | 横並びカード | グリッド・番号付き・アイコン |
| AXIS 説明 | 1文のみ | 3機能（通知・分析・次回購入）詳細 |
| Recommend カード | 縦積み | 3列横並び（1280px） |
| 除外候補 | 最大2件 | 最大3件 |

## v1.0 完了条件

- [x] 7 画面完走（Opening → Closing）
- [x] オフライン fallback（Neo4j 停止でも完走）
- [x] 7 分台本
- [x] 投影確認（1920px レイアウト対応）
- [x] テスト通過（12/12）

## Phase 4（将来）への引き継ぎ

- LLM トーク生成（Claude API 統合）
- Supabase セッション永続化（現在メモリ）
- 本番 AXIS 連携
- 多言語対応
- A/B テスト基盤
