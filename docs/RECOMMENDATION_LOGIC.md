# 推薦ロジック詳細仕様

## 概要

Knowledge Graph型レコメンドシステムの推薦ロジック全体像と実装詳細。

**バージョン**: v3 (2026年5月更新)  
**実装ファイル**: `engine/recommendation_engine.py`, `engine/demo_profile.py`

---

## 推薦フロー全体像

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Quick Questions 回答（5問）                          │
│  - q1_decision_style: 意思決定スタイル                       │
│  - q2_stress_handling: ストレス対処                          │
│  - q3_priority: 日々の優先事項                               │
│  - q4_change: 変化への態度                                   │
│  - q5_time_usage: 時間の使い方                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: 「あなたの価値観」5軸スコア算出                     │
│  config/score-weights.json に基づく重み付け加算              │
│  - safety (安心): 0-100                                      │
│  - family (家族): 0-100                                      │
│  - efficiency (効率): 0-100                                  │
│  - enjoyment (楽しさ): 0-100                                 │
│  - adventure (冒険): 0-100                                   │
│                                                              │
│  ※最大値を100にスケール                                     │
│  ※減衰係数 0.92^(質問数-順位) で新しい質問を重視             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: KG Needs 抽出（55種類のうち該当するもの）            │
│  config/need-mapping.json の answer_to_needs マッピング      │
│                                                              │
│  例: q3_priority = "family_time" の場合                      │
│    → FamilyComfort                                           │
│    → WeekendFamilyTrip                                       │
│    → ChildSafety                                             │
│    → EasyChildPickup                                         │
│                                                              │
│  全5問の回答から 5〜15個の Needs が抽出される                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Capability 抽出                                      │
│  config/need-mapping.json の need_to_capabilities マッピング │
│                                                              │
│  Need → Capability の対応（例）:                             │
│    ChildSafety → SafetyPerformance                           │
│    FamilyComfort → FamilyFriendly                            │
│    DrivingEnjoyment → DesignAppeal                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: 車種スコアリング                                     │
│  全車種（3,817台）に対してスコアを計算                       │
│                                                              │
│  総合スコア = Need Match (45%)                               │
│             + Feature Match (25%)                            │
│             + Similar Consumer (20%)                         │
│             + EvalCriteria (10%)                             │
│             + Load Boost (0-20pt)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: 推薦結果                                             │
│  - 上位3台を推薦                                             │
│  - 4〜6位を除外理由付きで表示                                │
│  - Decision Style に合わせた説明を生成                       │
└─────────────────────────────────────────────────────────────┘
```

---

## STEP 2: 価値観スコア算出詳細

### 実装: `engine/demo_profile.py`

#### スコア計算式

```python
# 各軸の raw スコアを計算
for i, answer in enumerate(sorted_answers):
    factor = decay ** (len(sorted_answers) - 1 - i)  # decay = 0.92
    
    for axis, delta in answer_weights[question_id][answer_key].items():
        raw_scores[axis] += delta * factor

# 正規化（最大値を100にスケール）
peak = max(raw_scores.values())
normalized_scores = {
    axis: (raw_scores[axis] / peak) * 100.0
    for axis in axes
}
```

#### 重み付けの例 (`config/score-weights.json`)

**質問3: 日々の生活で、最も大切にしていることは？**

| 回答選択肢 | safety | family | efficiency | enjoyment | adventure |
|-----------|--------|--------|------------|-----------|-----------|
| 安全・安心 | +28 | +10 | - | - | - |
| 効率・合理性 | +8 | - | +28 | - | - |
| 家族との時間 | +10 | +28 | - | - | - |
| 自己成長・学び | - | - | +18 | +12 | - |
| 楽しさ・充実感 | - | - | - | +26 | +14 |

#### 減衰係数の適用

新しい質問ほど重視される：

```
質問1: factor = 0.92^4 = 0.716
質問2: factor = 0.92^3 = 0.779
質問3: factor = 0.92^2 = 0.846
質問4: factor = 0.92^1 = 0.920
質問5: factor = 0.92^0 = 1.000  ← 最も重視
```

---

## STEP 3: KG Needs 抽出詳細

### 実装: `engine/demo_profile.py` + `config/need-mapping.json`

#### マッピング構造

```json
{
  "answer_to_needs": {
    "q1_decision_style": {
      "compare_thoroughly": [
        "DrivingConfidence",
        "LongTermReliability",
        "MaintenanceCostReduction"
      ],
      "intuition": [
        "DrivingEnjoyment",
        "PersonalExpression",
        "EmotionalAttachment"
      ]
    },
    "q3_priority": {
      "family_time": [
        "FamilyComfort",
        "WeekendFamilyTrip",
        "ChildSafety",
        "EasyChildPickup"
      ]
    }
  }
}
```

#### 抽出ロジック

```python
needs_set = set()

for answer in answers:
    qid = answer["question_id"]
    key = answer["answer_key"]
    
    # config から該当する Needs を取得
    mapped_needs = answer_to_needs.get(qid, {}).get(key, [])
    needs_set.update(mapped_needs)

# 結果: ["FamilyComfort", "ChildSafety", "DrivingConfidence", ...]
```

#### 補強ロジック (kg_need_resolver.py)

価値観スコアに基づいて追加 Needs を推論：

```python
# 上位2軸に関連する Needs を追加
top_2_axes = sorted(profile_scores.items(), key=lambda x: -x[1])[:2]

for axis, score in top_2_axes:
    if score > 60:
        # axis="family" → ["FamilyComfort", "ChildSafety", ...]
        additional_needs = AXIS_TO_NEEDS[axis]
        needs_set.update(additional_needs)
```

---

## STEP 4.5: プロファイル入力によるフィルタリング

### 概要

Quick Questions の前に、ユーザーは以下を入力します：
- **乗車人数** (family_size)
- **予算** (budget_min / budget_max)

これらの情報は、スコアリング前の**事前フィルタリング**に使用され、明らかに不適合な車種を除外します。

### 実装: `engine/recommendation_engine.py` の `recommend()` メソッド

#### フィルタリングロジック

```python
def recommend(self, req: RecommendationRequest, top_k: int = 3):
    vehicles = self._get_all_vehicles()  # 全3,817車種
    
    budget_min = req.budget_min if req.budget_min > 0 else req.budget
    budget_max = req.budget_max if req.budget_max > 0 else req.budget * 1.2
    
    scored = []
    for v in vehicles:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1. 予算フィルター（柔軟）
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        min_price, max_price = self._parse_price_range(v.get("price_range"))
        
        # 車種の最低価格が予算上限の120%を超える → スキップ
        if min_price > budget_max * 1.2:
            continue
        
        # 車種の最高価格が予算下限の80%未満 → スキップ
        if max_price < budget_min * 0.8:
            continue
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2. 定員フィルター（厳密）
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        seating = v.get("seating") or 0
        if req.family_size > 0 and seating > 0:
            # 車種の定員が家族人数より少ない → スキップ
            if seating < req.family_size:
                continue
        
        # ↓ ここまで到達した車種だけスコアリング対象
        need_score = self._score_need_match(v["name"], req.needs)
        # ... (スコア計算続く)
```

---

### 1. 予算フィルター（柔軟）

#### 許容範囲

- 予算上限の **+20%** まで許容（グレードアップの可能性を考慮）
- 予算下限の **-20%** まで許容（装備を抑えた選択肢を考慮）

#### フィルタリング条件

| 条件 | 結果 |
|------|------|
| 車種最低価格 > 予算上限 × 1.2 | ❌ スキップ（明らかに高すぎる） |
| 車種最高価格 < 予算下限 × 0.8 | ❌ スキップ（明らかに安すぎる） |
| 上記以外 | ✅ スコアリング対象 |

#### 具体例

**ユーザー入力**: 予算 200万円 〜 300万円

| 車種価格帯 | 判定 | 理由 |
|-----------|------|------|
| 150万円 〜 250万円 | ✅ OK | 範囲が重複（200万円台で選択可能） |
| 180万円 〜 350万円 | ✅ OK | 範囲が重複（200〜300万円で選択可能） |
| 280万円 〜 420万円 | ✅ OK | 範囲が重複（上限360万円まで許容） |
| 370万円 〜 500万円 | ❌ スキップ | 最低370万円は上限300万×1.2=360万円超 |
| 100万円 〜 150万円 | ❌ スキップ | 最高150万円は下限200万×0.8=160万円未満 |

---

### 2. 定員フィルター（厳密）

#### フィルタリング条件

```
車種定員 ≥ 家族人数
```

このフィルターは**厳密**で、余裕を持たせません。

#### 具体例

**ユーザー入力**: 家族 5人

| 車種定員 | 判定 | 理由 |
|---------|------|------|
| 7人乗り | ✅ OK | 5人全員乗車可能 |
| 5人乗り | ✅ OK | ちょうど5人 |
| 4人乗り | ❌ スキップ | 1人乗れない |
| 2人乗り | ❌ スキップ | 3人乗れない |

**注意**: 定員ぴったりの車種も含まれます（5人家族 → 5人乗りOK）。荷物スペースの必要性は Need マッチングで考慮されます。

---

### フィルタリング効果の試算

#### シナリオ: 家族5人、予算250万円〜350万円

**全3,817車種に対して:**

1. **定員フィルター適用後**: 
   - 2〜4人乗り（約1,300車種）を除外
   - 残り: 約2,500車種

2. **予算フィルター適用後**:
   - 420万円以上（約1,000車種）を除外
   - 200万円以下（約700車種）を除外
   - 残り: 約800車種

3. **スコアリング**:
   - 800車種に対してスコア計算
   - 上位3台を推薦
   - 4〜6位を除外車種として表示

#### パフォーマンス効果

- **フィルタリング前**: 3,817車種をスコアリング → 重い
- **フィルタリング後**: 約800車種をスコアリング → **79%削減**

---

### 除外理由への反映

フィルタリングで除外された車種は、推薦結果に含まれませんが、スコア上位でも除外された場合は「除外車種」として理由付きで表示されます。

**例** (`recommend_service.py` の `_generate_exclude_reason`):

```python
# 定員不足
if vehicle.seating < user.family_size:
    return f"乗車定員{vehicle.seating}人では家族{user.family_size}人の移動に不足するため"

# 予算オーバー
if vehicle.min_price > user.budget_max * 1.3:
    return f"予算上限（{user.budget_max // 10000}万円）に対し価格帯が高すぎるため"
```

---

## STEP 5: 車種スコアリング詳細

### 実装: `engine/recommendation_engine.py`

### 総合スコア計算式

```python
total_score = (
    need_match_score * 0.45 +
    feature_match_score * 0.25 +
    similar_consumer_score * 0.20 +
    eval_criteria_score * 0.10
) * 100 + load_boost
```

---

### 1. Need Match Score (45%)

#### Neo4j クエリパス

```cypher
MATCH (v:VehicleModel {name: $vehicle_name})
      -[:HAS_FEATURE]->(tf:TechnicalFeature)
      -[:REALIZES]->(cap:Capability)
      -[:SUPPORTS]->(n:Need)
WHERE n.name IN $user_needs
RETURN collect(DISTINCT n.name) AS matched_needs
```

#### スコア計算

```python
matched_needs = _vehicle_graph_needs(vehicle_name)  # 車種がサポートするNeeds
user_needs = {"FamilyComfort", "ChildSafety", "DrivingConfidence"}

matched_count = len(matched_needs & user_needs)
need_match_score = min(matched_count / len(user_needs), 1.0)

# 例: 3/3マッチ → 1.0 (100%)
# 例: 2/3マッチ → 0.67 (67%)
```

---

### 2. Feature Match Score (25%)

#### ロジック

TechnicalFeature のテキストと Need キーワードの一致を確認。

```python
NEED_KEYWORDS = {
    "safety": ["安全", "safety", "セーフティ", "衝突", "AEB", "ブレーキ"],
    "family": ["ファミリー", "子ども", "チャイルド", "スライド", "後席"],
    "fuel_efficiency": ["燃費", "ハイブリッド", "電気", "eco", "HV"],
}

# VehicleModel の全 TechnicalFeature を取得
features_text = " ".join(feature.name for feature in vehicle.features)

matched = 0
for need in user_needs:
    keywords = NEED_KEYWORDS.get(need, [need])
    if any(kw in features_text for kw in keywords):
        matched += 1

feature_match_score = min(matched / len(user_needs), 1.0)
```

#### 例

**ユーザーのNeeds**: ["family", "safety", "fuel_efficiency"]  
**N-BOX の TechnicalFeature**:
- "Honda SENSING（先進安全装備）"
- "スライドドア"
- "ハイブリッドシステム"

→ 全3つマッチ → **1.0 (100%)**

---

### 3. Similar Consumer Score (20%)

#### Neo4j クエリ

```cypher
MATCH (c:Consumer)-[:OWNED]->(vo:VehicleOwnership {is_current: true})
      -[:OF_MODEL]->(v:VehicleModel {name: $vehicle_name})
RETURN c.id AS consumer_id,
       c.family_size AS family_size
LIMIT 200
```

#### 類似度計算

```python
for consumer in selectors:
    # 1. 家族人数の類似度
    size_diff = abs(consumer.family_size - user_family_size)
    size_similarity = max(0, 1 - size_diff / 5)
    
    # 2. Need の重複度
    consumer_needs = get_consumer_needs(consumer.id)
    need_overlap = len(consumer_needs & user_needs) / len(user_needs)
    
    # 3. 総合類似度
    similarity = (size_similarity * 0.4 + need_overlap * 0.6)
    scores.append(similarity)

# 上位20人の平均
similar_consumer_score = mean(sorted(scores, reverse=True)[:20])
```

---

### 4. Evaluation Criteria Score (10%)

#### ロジック

ユーザーのNeedsと一致する EvaluationCriteria を多く持つ車種を高評価。

```cypher
MATCH (v:VehicleModel {name: $vehicle_name})
      <-[:SELECTED]-(c:Consumer)-[:VALUED]->(ec:EvaluationCriteria)
WHERE ec.label IN $user_capabilities
RETURN count(DISTINCT ec) AS matched_criteria
```

#### スコア

```python
matched_criteria = query_result
total_criteria = len(user_capabilities)

eval_criteria_score = min(matched_criteria / max(total_criteria, 1), 1.0)
```

---

### 5. Load Boost (0-20pt 加算)

#### 概要

質問回答から検出された「負荷」に対応する機能を持つ車種にボーナス。

**検出される負荷の例** (`config/score-weights.json` の `load_labels`):
- "問題解決への負荷"
- "他者への依存"
- "慎重な検討が必要"
- "家族時間の優先"

#### マッピング (`config/load-feature-mapping.json`)

```json
{
  "load_to_features": {
    "問題解決への負荷": {
      "features": ["Honda SENSING", "運転支援システム", "安全装備"],
      "boost": 5.0
    },
    "家族時間の優先": {
      "features": ["スライドドア", "3列シート", "広い室内"],
      "boost": 8.0
    }
  }
}
```

#### スコア加算

```python
load_boost = 0.0

for load in detected_loads:
    mapping = load_mapping.get(load, {})
    target_features = mapping.get("features", [])
    boost_value = mapping.get("boost", 0.0)
    
    # 車種が対象機能を持つか確認
    if any(feat in vehicle_features for feat in target_features):
        load_boost += boost_value

# 最大20ptまで
load_boost = min(load_boost, 20.0)
```

---

## STEP 6: 推薦結果生成

### 上位3台の選定

```python
# スコアでソート
ranked = sorted(all_scores, key=lambda x: x.total_score, reverse=True)

recommendations = ranked[:3]
excluded = ranked[3:6]  # 4〜6位を除外車種として表示
```

### 推薦理由の生成

```python
# 1位の理由例
reason = f"""
あなたの価値観（{dominant_axis_label}）に最もマッチする車種です。
{len(matched_needs)}個の重視する欲求に対応しています。

【対応するニーズ】
- {need_1_label}
- {need_2_label}
- {need_3_label}

【類似した購入者】
家族{family_size}人構成の購入者が{similar_count}名選んでいます。
"""
```

### 除外理由の生成

**`recommend_service.py` の `_generate_exclude_reason` 関数**

```python
# 定員不足
if vehicle.seating < user_family_size:
    return f"乗車定員{vehicle.seating}人では家族{user_family_size}人の移動に不足するため"

# 予算オーバー
if vehicle.min_price > user_budget_max * 1.3:
    return f"予算上限（{user_budget_max // 10000}万円）に対し価格帯が高すぎるため"

# ニーズ不一致
if "family" in user_needs and vehicle.seating < 5:
    return "家族利用を重視する場合、より多人数対応の車種が適しているため"

# デフォルト
return "重視する価値観・利用シーンとの適合度が、上位3台より低いため"
```

---

## Decision Style による説明カスタマイズ

### 6つのDecision Style

1. **Maximizer（徹底比較型）** - 詳細なスペック比較を提示
2. **Satisficer（十分型）** - 必要十分な情報に絞る
3. **Authority-driven（権威依存型）** - 専門家評価・ランキングを強調
4. **Delegator（委任型）** - 他の購入者のレビュー・推薦を提示
5. **Intuitive（直感型）** - ビジュアル・感性訴求を重視
6. **Impulsive（衝動型）** - 簡潔・即決を促す

### 説明スタイルの例

**Maximizer向け:**
```
【詳細スペック比較】
N-BOX vs. タント vs. スペーシア
- 室内長: 2,180mm vs. 2,180mm vs. 2,155mm
- 燃費: 21.2km/L vs. 21.2km/L vs. 22.2km/L
- 価格: 142万円〜 vs. 136万円〜 vs. 138万円〜
```

**Delegator向け:**
```
【購入者の声】
「家族4人でも広々。スライドドアが本当に便利！」（30代・家族4人）
「Honda SENSINGで安心して運転できます」（40代・家族3人）
```

---

## パフォーマンス最適化

### キャッシュ戦略

1. **セッションレベル**: 推薦結果を `session_store` にキャッシュ
2. **車種メタデータ**: `_vehicle_meta` の結果をメモリキャッシュ
3. **Neo4jクエリ最適化**: インデックス活用、LIMIT句の適切な使用

### スケーラビリティ

- **並列処理**: 車種スコアリングは独立 → 将来的に並列化可能
- **段階的フィルタリング**: 事前に定員・予算で絞り込み → スコアリング対象を削減
- **Fallback機能**: Neo4j接続失敗時は静的JSONから推薦

---

## 設定ファイル一覧

| ファイル | 役割 |
|---------|------|
| `config/score-weights.json` | 価値観スコア重み付け |
| `config/need-mapping.json` | 回答→Need、Need→Capability マッピング |
| `config/decision-style-weights.json` | Decision Style 判定の重み付け |
| `config/load-feature-mapping.json` | Load → Feature マッピング |
| `data/demo/fallback/recommend.json` | Fallback用の静的推薦データ |

---

## テスト・検証

### 推薦結果の妥当性確認

```python
# テストケース1: 家族重視ユーザー
user_profile = {
    "family": 90,
    "safety": 70,
    "efficiency": 50,
    "enjoyment": 30,
    "adventure": 20
}
# 期待: ステップワゴン、N-BOX、フリード

# テストケース2: 楽しさ重視ユーザー
user_profile = {
    "enjoyment": 95,
    "adventure": 75,
    "efficiency": 40,
    "family": 30,
    "safety": 20
}
# 期待: シビック タイプR、S660、CR-Z
```

### ロギング

```python
logger.info(f"User needs: {user_needs}")
logger.info(f"Detected loads: {detected_loads}")
logger.info(f"Top 3: {[r.model for r in recommendations]}")
logger.info(f"Scores: {[(r.model, r.score) for r in recommendations]}")
```

---

## 今後の改善案

1. **機械学習の導入**: 購入者データから Need → VehicleModel の直接予測
2. **リアルタイムフィードバック**: ユーザーの選択を学習して推薦精度向上
3. **A/Bテスト**: スコアリング重み付けの最適化
4. **多目的最適化**: スコアだけでなく、多様性・新規性も考慮

---

## 参考資料

- **グラフスキーマ**: `CLAUDE.md`
- **Quick Questions設計**: `docs/QUICK_QUESTIONS_LOGIC.md`
- **Decision Style設計**: `docs/DECISION_STYLE_QUICK_QUESTIONS_PLAN.md`
- **Load Boost実装**: `docs/LOAD_BOOST_IMPLEMENTATION.md`
