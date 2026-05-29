# Decision Intelligence PoC — 迷わせないレコメンド

**バージョン**: v1.1 (Phase 4.3 完了)  
**最終更新**: 2026-05-27  
**リポジトリ**: https://github.com/hono-del/Sales-Recommendation

自動車購入における意思決定支援システムのショールームデモ。Knowledge Graph で「なぜその提案か」を可視化し、説明可能な推薦を実現します。

---

## クイックスタート

```powershell
# 1. Neo4j Desktop で「Recommendation」インスタンスを起動

# 2. デモ起動（API + Next.js）
cd "C:\Users\a01380\OneDrive - CMC Corporation\デスクトップ\次世代商談"
.\start-demo.ps1

# 3. ブラウザで開く
# → http://localhost:3000/demo/opening
```

**所要時間**: 7〜10分  
**画面数**: 8画面（Opening → Profile → Questions (4問) → Delegation → Graph → Recommend → Dealer → Closing）

---

## システム構成

| コンポーネント | 技術 | ポート | 用途 |
|---------------|------|--------|------|
| **フロントエンド** | Next.js 15 + TypeScript | 3000 | デモ UI・KG 可視化 |
| **API** | FastAPI + Python | 8000 | セッション・推薦・グラフ |
| **グラフ DB** | Neo4j Desktop | 7687 | Knowledge Graph (v3 オントロジー) |

---

## 主要機能

### Phase 0: 基盤（完了）
- API 契約確定
- Next.js 雛形
- Supabase migration（将来用）
- fallback JSON

### Phase 1: MVP（完了）
- ✅ **SCR-01** Opening（課題提示）
- ✅ **SCR-02** Quick Questions（4問 + ProfileMap）
- ✅ **SCR-03** AI Delegation（Guide / Co-pilot / Auto）
- ✅ **SCR-05** Recommendation（簡易版）
- ✅ Demo fallback（Neo4j 不可時も完走）

### Phase 2: KG 主役（完了）
- ✅ **SCR-04** Knowledge Graph Visualization
  - react-force-graph-2d 段階アニメーション
  - Why Panel（重視価値・負荷・ロジック）
  - NarrationBar（5秒自動切替）
- ✅ **SCR-05** Recommendation 完全版
  - 3カード横並び（1280px）
  - 除外候補 最大3件
  - 訴求ポイント（appeal_points）
  - Delegation 連動表示
- ✅ graph-path API（Neo4j v3 Cypher）
- ✅ パフォーマンス（120秒 TTL キャッシュ、ノード上限 50）

### Phase 3: OEM ストーリー（完了）
- ✅ **SCR-06** Dealer Support
  - KPI 3指標（マッチ度・車種・タイプ）
  - 顧客インサイト
  - 提案トーク（LLM 生成 / テンプレート）
  - 次のアクション
- ✅ **SCR-07** AXIS Closing
  - 購入後ジャーニー（4ステップ）
  - AXIS 連携イメージ
  - PoC 明示
- ✅ オペレーターガイド（`docs/OPERATOR_GUIDE.md`）

### Phase 4: Load Boost & Profile Input & 思考プロセス UI（完了）

#### 4.1 Load Boost（完了）
- ✅ **Load 検出の推薦統合**
  - Quick Questions で検出した負荷・不安（Load）を推薦ロジックに統合
  - 不安を解消する機能を持つ車種のスコアをブースト（0-20点）
  - 推薦理由に Load 対応機能を明記
  - 例: 駐車不安 → パノラミックビューモニター搭載車を推薦
- ✅ Load → Feature マッピング（`config/load-feature-mapping.json`）
- ✅ 推薦エンジン拡張（`engine/recommendation_engine.py`）
- ✅ テストケース（`tests/test_load_boost.py`）
- ✅ ドキュメント（`docs/LOAD_BOOST_IMPLEMENTATION.md`）

#### 4.2 Profile Input（完了）
- ✅ **Profile Input 画面（人数・予算ヒアリング）**
  - 乗車人数（1人/2人/3-4人/5-6人/7人以上）
  - 予算範囲（~200万/200-300万/300-400万/400-500万/500万~）
  - Quick Questions との組み合わせで推薦精度向上
  - 例: 4人 + 家族中心 → ファミリー向け、4人 + 一人時間 → 多用途対応
- ✅ 設計書（`docs/PROFILE_INPUT_DESIGN.md`）
- ✅ Q5 削除と Delegation 画面統合（UX改善）

#### 4.3 思考プロセス UI 全面改善（完了）
- ✅ **「なぜこの提案か」画面を5ステップ構造に変更**
  - 従来: 複雑な Knowledge Graph → 理解負荷が高い
  - 改善: 線形の思考プロセス表示 → 一瞬で理解
- ✅ **5ステップフロー**
  1. あなたの価値観
  2. 検出された負荷
  3. 必要な体験（新規）
  4. 必要な機能（理由付き）
  5. おすすめ車種
- ✅ **AIの判断理由パネル（自然言語化）**
  - 数式表記を廃止
  - 「人に説明できる推薦理由」に変更
- ✅ 新コンポーネント
  - `ThinkingProcessView.tsx` - 5ステップカード型UI
  - `AIReasoningPanel.tsx` - 自然言語化された判断理由
- ✅ バックエンド拡張
  - `_build_thinking_process()` - 5ステップデータ生成
  - 負荷 → 体験、機能 → 理由のマッピング
- ✅ 設計書（`docs/THINKING_PROCESS_UI_REDESIGN.md`）
- ✅ graph-path API タイムアウト延長（8秒 → 15秒）

---

## ディレクトリ構造

```
次世代商談/
├── api/                      # FastAPI
│   ├── api_server.py         # メイン（旧 PoC API）
│   └── demo/                 # デモ専用 API
│       ├── router.py         # エンドポイント
│       ├── session_store.py  # セッション管理（メモリ）
│       ├── graph_path_service.py  # KG パス生成
│       └── recommend_service.py   # 推薦ロジック
├── demo-web/                 # Next.js 15
│   ├── src/
│   │   ├── app/demo/         # 7画面（page.tsx）
│   │   ├── components/demo/  # Client コンポーネント
│   │   ├── lib/              # api-client, graph-animation
│   │   ├── stores/           # demoStore (Zustand)
│   │   └── types/            # TypeScript 型定義
│   └── package.json
├── engine/                   # 推薦エンジン
│   ├── recommendation_engine.py  # Neo4j v3 推薦
│   └── demo_profile.py       # プロファイル計算
├── graph/                    # グラフ構築
│   └── graph_builder.py      # Neo4j v3 オントロジー
├── data/
│   ├── raw/consumer_stories.json  # 元データ（4,205件）
│   ├── processed/            # 抽出済み構造化データ
│   └── demo/fallback/        # Neo4j 不可時の固定 JSON
├── tests/                    # pytest
│   ├── test_demo_api.py
│   ├── test_phase1_recommend.py
│   └── test_phase2_graph_path.py
├── docs/
│   ├── design/               # Phase 完了チェックリスト
│   ├── output/               # 要件定義書・設計書
│   └── OPERATOR_GUIDE.md     # オペレーター向けマニュアル
├── CLAUDE.md                 # プロジェクトコンテキスト
├── start-demo.ps1            # デモ起動スクリプト
└── README.md                 # このファイル
```

---

## 開発コマンド

### デモ起動

```powershell
.\start-demo.ps1
```

### 手動起動

```powershell
# API（port 8000）
$env:NEO4J_PASSWORD="recommendation"
py -m uvicorn api.api_server:app --host 0.0.0.0 --port 8000

# Next.js（port 3000）
cd demo-web
npm run dev
```

### グラフ再構築

```powershell
$env:NEO4J_PASSWORD="recommendation"
py graph_builder.py
```

### テスト

```powershell
# 全テスト
py -m pytest tests/ -q

# Phase 別
py -m pytest tests/test_phase1_recommend.py -v
py -m pytest tests/test_phase2_graph_path.py -v
```

---

## Vercel デプロイ（社内共有用）

### 前提条件
- GitHubリポジトリ: https://github.com/hono-del/Sales-Recommendation
- Vercelプロジェクト: https://vercel.com/hono-2482s-projects/sales-recommendation

### デプロイ手順

1. **Vercelダッシュボードでリポジトリを接続**
   - https://vercel.com/hono-2482s-projects/sales-recommendation にアクセス
   - "Connect Git Repository" をクリック
   - `hono-del/Sales-Recommendation` を選択

2. **プロジェクト設定**
   - **Root Directory**: `demo-web`
   - **Framework Preset**: Next.js
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
   - **Install Command**: `npm install`

3. **環境変数（後でAPI統合時に設定）**
   ```
   NEXT_PUBLIC_API_URL=https://your-api-url.com
   ```

4. **デプロイ**
   - "Deploy" をクリック
   - 自動ビルド完了後、URLが発行されます

### 注意事項
- 現在はフロントエンドのみデプロイ（APIは別途必要）
- APIなしでは一部機能が動作しません（fallbackで最低限動作）
- Neo4jデータベースは含まれません

---

## トラブルシューティング

| 問題 | 対処 |
|------|------|
| **Graph が空** | Neo4j Desktop で "Recommendation" を Start |
| **API エラー** | `curl http://localhost:8000/health` で確認 |
| **Demo Mode バナー** | Neo4j 停止中の fallback（完走は可能） |
| **port 8000 使用中** | `Get-NetTCPConnection -LocalPort 8000 \| Stop-Process` |

---

## 成果物・KPI

| 項目 | 目標 | 実績 |
|------|------|------|
| デモ完走率 | 100% | ✅ 7画面完走 + fallback 対応 |
| KG 表示 | 5秒以内 | ✅ キャッシュ + アニメスキップ |
| テスト通過 | 全 pass | ✅ 18/18 passed |
| 画面数 | 7 | ✅ SCR-01〜07 |
| 体験時間 | 7〜10分 | ✅ 台本通り 7分 |

---

## 今後の拡張（Phase 4〜）

- [ ] Claude API 統合（LLM トーク生成）
- [ ] Supabase セッション永続化
- [ ] 本番 AXIS 連携
- [ ] A/B テスト基盤
- [ ] 多言語対応
- [ ] 販売店向け管理画面

---

## ドキュメント

- [CLAUDE.md](./CLAUDE.md) — プロジェクト全体のコンテキスト
- [OPERATOR_GUIDE.md](./docs/OPERATOR_GUIDE.md) — デモ操作マニュアル
- [SERVICE_OFFERING_CATALOG_WORK_GUIDE.md](./docs/SERVICE_OFFERING_CATALOG_WORK_GUIDE.md) — 社内サービス案カタログ整備（担当者向け）
- [service-offerings-catalog.xlsx](./data/templates/service-offerings-catalog.xlsx) — 上記の Excel 記入テンプレート
- [phase3-completion.md](./docs/design/phase3-completion.md) — Phase 3 完了チェックリスト
- [detailed_requirements_specification.md](./docs/output/detailed_requirements_specification.md) — 要件定義書

---

## ライセンス

PoC 用途。商用利用は別途契約。

## 連絡先

開発チーム: （連絡先）
