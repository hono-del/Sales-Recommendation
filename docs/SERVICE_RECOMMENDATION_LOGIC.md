# サービスレコメンド 推薦ロジック

## 概要

ユーザーの価値観（5つの質問への回答）に基づいて、最適なアップグレード・ダウングレードサービスを提案するシステム。

車種レコメンドとは異なり、**乗車人数・予算の入力は不要**で、純粋に価値観だけでサービスをマッチングする。

## データ構造

### ServiceOffering ノード（Neo4j）

```cypher
(:ServiceOffering {
  id: "S-1",                      // サービスID
  title: "定額メンテナンスプラン",    // サービス名
  one_liner: "月額固定で...",        // 一行説明
  direction: "upgrade",            // upgrade/downgrade/neutral
  domain: "maintenance",           // サービスドメイン
  lifecycle: "ownership",          // ライフサイクルステージ
  pitch_template: "...",           // 営業トーク
  need_rationale: "...",           // 推薦理由
  load_labels: ["維持費への不安"],  // 軽減する負荷
  value_axes: ["効率", "安心"]     // 強化する価値軸
})
```

### ServiceOffering -[:ADDRESSES]-> Need

- サービスが対応する Need へのリレーション
- `priority`: 1-3（primary）, 11-12（secondary）で重要度を表現

## 質問設計（5問）

### 質問1: 生活改善ニーズ
「現在の生活で、最も改善したいことは？」
- 手間や負担を減らす
- 体験の質を上げる
- つながりを増やす
- コストを抑える
- 柔軟に使い分ける

### 質問2: テクノロジー姿勢
「デジタルやテクノロジーに対して、あなたは？」
- 積極的に試す
- 便利であれば使う
- 必要なものだけ厳選
- 安全性を確認
- シンプル・最小限

### 質問3: コミュニティ価値観
「コミュニティや人とのつながりについて、あなたは？」
- 積極的に参加
- 知識を共有
- 情報収集のため
- 必要なときだけ
- 独立して行動

### 質問4: 利用スタイル
「モノやサービスの利用について、あなたの考えは？」
- 所有したい
- サブスク好き
- 従量課金が合理的
- シェア・レンタル
- 使い分ける

### 質問5: ライフスタイル変化
「今後のライフスタイルの変化について、あなたは？」
- 予測して準備
- 柔軟に対応
- アップグレード
- シンプル化
- 維持・安定

## スコアリングロジック

### 総合スコア計算式（v2.0 - Load重視）

```
総合スコア = Need Match × 40% + Load Match × 40% + Value Alignment × 20%
```

**変更理由（2026-06-02）**：
- Load検出の精緻化に伴い、Load Matchの影響度を30%→40%に引き上げ
- ユーザーの懸念事項（飽き性、ケチりがち、使いこなせない不安など）をより的確に捉えて推薦に反映

### 1. Need Match スコア（40%）

ユーザーの Need とサービスが ADDRESSES する Need のマッチング。

```python
# Priority 加重スコア
weighted_score = 0.0
for matched_need in matched_needs:
    if need.priority <= 3:  # primary
        weight = 1.0
    else:  # secondary (11-12)
        weight = 0.5
    weighted_score += weight

# 正規化（最大 = ユーザーNeeds数）
need_score = min(weighted_score / len(user_needs), 1.0)
```

**例**:
- ユーザー Need: 3件
- サービス A が primary Need 2件にマッチ → weighted_score = 2.0 → score = 2.0/3 = **0.67**
- サービス B が primary 1件 + secondary 1件 → weighted_score = 1.5 → score = 1.5/3 = **0.50**

### 2. Load Match スコア（40%）

ユーザーの検出された負荷（Load）と、サービスが軽減する負荷のマッチング。

#### Load検出ロジック（v2.0 - ルールベース）

ユーザーの回答パターンから、以下の10種類のLoadを検出：

| Load名 | 検出条件（例） | 説明 |
|--------|--------------|------|
| すぐ飽きるリスク | 新技術好き + 探索志向 + トレンド追従 | 新しいもの好きで、長期利用に向かない |
| 機能不足による後悔 | 効率重視 + コスト重視 + 最適化志向 | ケチりがち・大雑把で後から後悔しやすい |
| 短期間で乗り換えるリスク | 探索志向 + 柔軟な所有形態 + アップグレード志向 | 頻繁に乗り換える傾向 |
| 維持費への不安 | コスト最適化 + 安全優先 | 維持費が気になる |
| 時間・手間への不安 | 効率重視 + 計画的 + 手間削減志向 | 時間や手間がかかることを嫌う |
| 使いこなせない不安 | 慎重派 + 技術消極的 + ミニマル志向 | 新しい機能に不安を感じる |
| 短期利用による割高感 | コスト重視 + 従量課金志向 | 使い方次第で割高になる懸念 |
| 家族同意への不安 | 家族・他者重視 + 意見収集型 | 家族の同意が必要 |
| 孤独感の懸念 | 独立志向 + 個人的成長重視 | つながりの欠如による孤独感 |
| 契約ストレス | 慎重派 + 安定維持志向 | 契約手続きへの抵抗感 |

**検出ルール定義ファイル**: `config/load-detection-rules.json`

各Loadは以下の形式で定義：
```json
{
  "すぐ飽きるリスク": {
    "triggers": [
      {"question_id": "q4_change", "answer_keys": ["follow_trend", "try_new"]},
      {"question_id": "sq2_technology_stance", "answer_keys": ["enthusiast"]},
      {"question_id": "sq5_life_change", "answer_keys": ["explore_options"]}
    ],
    "threshold": 2,
    "description": "新しいもの好き・トレンド追従・探索志向が強い → 飽きやすいリスク"
  }
}
```

#### Loadマッチングスコア計算

```python
# サービスの load_labels とユーザーの detected_loads の重複
matched_loads = [load for load in user_loads if load in service_loads]

# スコア = マッチ数 / ユーザーのLoad数
load_score = len(matched_loads) / len(user_loads)
```

**例**:
- ユーザー Load: ["維持費への不安", "機能不足による後悔"]（ケチりがちパターン）
- サービスの load_labels: ["維持費への不安"]
- マッチ: 1件 → score = 1/2 = **0.50**

### 3. Value Alignment スコア（20%）

ユーザーの価値観軸（5つのスコア）とサービスが強化する価値軸の整合性。

```python
# ユーザーの上位3軸を取得
user_top_axes = sorted(profile_scores.items(), key=lambda x: x[1], reverse=True)[:3]
user_top_axis_names = [axis for axis, _ in user_top_axes]

# サービスの value_axes との重複度
overlap = len(set(service_axes) & set(user_top_axis_names))
value_score = overlap / len(service_axes)
```

**価値軸の種類**:
- `safety`: 安全・安心
- `family`: 家族との時間
- `efficiency`: 効率・合理性
- `enjoyment`: 楽しさ・充実感
- `adventure`: 自己成長・学び

**例**:
- ユーザー上位軸: [efficiency:0.8, safety:0.7, family:0.5]
- サービス A の value_axes: ["efficiency", "safety"] → overlap = 2 → score = 2/2 = **1.0**
- サービス B の value_axes: ["adventure", "enjoyment"] → overlap = 0 → score = 0/2 = **0.0**

## 推薦フロー

```
1. ユーザーが5つの質問に回答
   ↓
2. 質問回答からプロファイル生成
   - mapped_needs（Need抽出）
   - detected_loads（Load検出）
   - profile_scores（価値観スコア）
   ↓
3. Neo4j から全 ServiceOffering を取得
   ↓
4. 各サービスをスコアリング
   - Need Match (50%)
   - Load Match (30%)
   - Value Alignment (20%)
   ↓
5. スコアでソート、上位5件を返却
   ↓
6. フロントエンドで表示
   - タイトル、説明
   - 適合度スコア
   - マッチした Need/Load
   - 営業トーク、推薦理由
```

## フィルタリング

### Direction フィルター（オプション）
- `upgrade`: アップグレードサービスのみ
- `downgrade`: ダウングレードサービスのみ
- `null`: 全て（デフォルト）

### Lifecycle フィルター（緩い）
- サービスの `lifecycle` とユーザーの `lifecycle_stage` のマッチング
- `ownership` サービスは全員に推薦可能（最も緩い条件）

### 最低閾値
- 総合スコアが **0.1 未満**のサービスは除外

## 設定ファイル

### config/service-questions.json
サービスレコメンド用の5つの質問定義。

```json
{
  "version": "1.0",
  "questions": [
    {
      "index": 1,
      "id": "sq1_lifestyle_satisfaction",
      "text": "現在の生活で、最も改善したいことは？",
      "choices": [...]
    },
    ...
  ]
}
```

### docs/0602_service-offerings-catalog_reviewed.xlsx
サービス提案のマスターデータ（44件）。

**主要列**:
- `id`: サービスID（S-1, S-2, ...）
- `title`: サービス名
- `one_liner`: 一行説明
- `direction`: upgrade/downgrade/neutral
- `domain`: maintenance/upgrade_path/connectivity/etc
- `lifecycle`: ownership/purchase/disposal
- `primary_need_1~3`: 主要Need（KG Need name）
- `secondary_need_1~2`: 副次Need
- `load_label_1~3`: 軽減する負荷
- `value_axis_1~2`: 強化する価値軸
- `pitch_template`: 営業トーク
- `need_rationale`: 推薦理由
- `eligibility`: 利用条件

## データインポート

```bash
# ServiceOffering データを Neo4j にインポート
py import_service_offerings.py
```

**処理内容**:
1. 既存の ServiceOffering ノードを削除
2. Excel から44件のサービスを読み込み
3. ServiceOffering ノードを作成
4. Need とのリレーション（ADDRESSES）を構築
5. load_labels, value_axes をプロパティとして保存

## パフォーマンス最適化

### Need Match の効率化
- Neo4j の IN 演算子で一括マッチング
- Priority で重要度を加重

### Load Match の効率化
- プロパティとして保存（専用ノード不要）
- Python 側でリスト比較

### Value Alignment の効率化
- プロパティとして保存
- ユーザーの上位3軸のみで比較

## API エンドポイント

### GET /api/demo/sessions/{session_id}/services

セッションに基づいたサービス推薦を返す。

**リクエスト**: なし（セッション情報を使用）

**レスポンス**:
```json
{
  "services": [
    {
      "id": "S-1",
      "title": "定額メンテナンスプラン",
      "one_liner": "月額固定で、突然の整備費不安を減らす",
      "direction": "upgrade",
      "domain": "maintenance",
      "score": 0.85,
      "matched_needs": ["MaintenanceCostReduction", "LongTermReliability"],
      "matched_loads": ["維持費への不安"],
      "value_alignment": 0.7,
      "pitch": "携帯の定額プランのように...",
      "need_rationale": "維持費の見通しが立つことで..."
    },
    ...
  ],
  "fallback": false
}
```

## 実装ファイル

### バックエンド
- `engine/service_recommendation_engine.py` - 推薦エンジン本体
- `api/demo/router.py` - FastAPI エンドポイント
  - `@router.get("/sessions/{session_id}/services")`

### フロントエンド
- `demo-web/src/app/demo/service/questions/page.tsx` - 質問ページ
- `demo-web/src/app/demo/service/recommend/page.tsx` - 結果ページ
- `demo-web/src/components/demo/ServiceQuestionsClient.tsx` - 質問UI
- `demo-web/src/components/demo/ServiceRecommendClient.tsx` - 結果UI
- `demo-web/src/components/demo/ServiceOfferingSection.tsx` - サービスカード表示

### データ・設定
- `config/service-questions.json` - 質問定義
- `docs/0602_service-offerings-catalog_reviewed.xlsx` - サービスカタログ
- `import_service_offerings.py` - データインポートスクリプト

## 今後の拡張

### Need マッピング強化
質問回答から Need を抽出するロジックを強化し、より正確なマッチングを実現。

### Load 検出の精緻化
質問回答から Load を推定するアルゴリズムの追加。

### Lifecycle 管理
ユーザーのライフサイクルステージ（purchase/ownership/disposal）に応じた推薦の最適化。

### Decision Style 統合
車種レコメンドで使用している Decision Style（意思決定スタイル）をサービス推薦にも適用。

### 推薦理由の生成
Claude API を使った、よりパーソナライズされた推薦理由の生成。

---

## 補足: 車種レコメンドとの違い

| 項目 | 車種レコメンド | サービスレコメンド |
|------|--------------|------------------|
| **入力** | 乗車人数・予算・5問 | 5問のみ |
| **質問内容** | 生活価値観（車に関係なし） | 生活価値観（サービス利用スタイル） |
| **推薦対象** | VehicleModel ノード | ServiceOffering ノード |
| **スコア要素** | Need・Feature・類似消費者・Load | Need・Load・Value軸 |
| **フィルタ** | 乗車人数・予算で絞り込み | Direction・Lifecycle で絞り込み |
| **Decision Style** | 提示方法に反映 | （未実装） |
| **営業トーク** | Claude API で生成 | テンプレートから取得 |

サービスレコメンドは車種レコメンドよりもシンプルで、ユーザーの価値観に焦点を当てた設計になっています。
