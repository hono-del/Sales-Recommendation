# Quick Questions の設計・ロジック整理

**作成日**: 2026-05-27  
**バージョン**: v1.0  
**対象システム**: Decision Intelligence PoC

---

## 📋 目的

**Quick Questions（5問）の目的**は以下の通りです：

### 1. **価値観・生活文脈・不安・負荷の理解**
- 顧客の **5つの価値軸**（安心・家族・効率・楽しさ・冒険）をスコア化
- **生活ニーズ**（Need）を特定（例: 子供の安全、運転の自信、燃費不安の軽減）
- **負荷・不安**（Load）を検出（例: 駐車不安、維持費不安、情報過多）

### 2. **リアルタイムフィードバック**
- 「あなた理解 MAP」で5軸スコアをリアルタイム更新
- 顧客が自分の価値観を視覚的に確認できる

### 3. **推薦の基盤データ生成**
- スコアとNeedをもとに、後続の車種推薦・機能マッチングに活用

---

## 🎯 5つの質問内容

| ID | 質問 | 選択肢 | 目的 |
|----|------|--------|------|
| **q1_value** | 最も大切にしたいことは？ | 安全・楽しさ・家族・効率・ステータス | **価値観の軸**を特定 |
| **q2_weekend** | 休日の過ごし方は？ | 家族中心・一人時間・アクティブ・学び・趣味 | **生活文脈**を把握 |
| **q3_regret** | 避けたい後悔は？ | 使わない・家族不満・維持費・飽きる・機能不足 | **不安・リスク**を検出 |
| **q4_stress** | 運転で気になることは？ | 疲労・渋滞・駐車・操作難・情報過多 | **負荷要因**を特定 |
| **q5_ai** | AIの役割は？ | AI決定・AI候補提示・自分決定 | **委任レベル**の傾向 |

---

## 🧮 スコア算出ロジック

### **1. プロファイルスコア（5軸）**

**アルゴリズム**:
```python
# 各回答にスコア配分（config/score-weights.json）
# 例: q1_value = "safety" → safety +28, family +8

raw_scores = { "safety": 0, "family": 0, "efficiency": 0, "enjoyment": 0, "adventure": 0 }

for 質問 in 回答順:
    factor = 0.92 ^ (残り質問数)  # 新しい回答ほど重視
    for 軸 in スコア配分:
        raw_scores[軸] += 配点 × factor

# 最大値を100にスケール
normalized = (各軸 / max値) × 100
```

**特徴**:
- ✅ **最新の回答ほど重視**（decay = 0.92）
- ✅ **複数軸に影響**（例: "safety"選択 → safetyだけでなく familyも+8）
- ✅ **正規化**で最大値を100%に調整

**実装ファイル**: `engine/demo_profile.py`

---

### **2. Need マッピング**

各回答は **具体的な生活ニーズ（Need）** にマッピングされます:

```json
// config/need-mapping.json
{
  "q1_value": {
    "safety": ["ChildSafety", "DrivingConfidence", "AccidentAnxietyReduction", "EasyParking"],
    "family": ["FamilyComfort", "WeekendFamilyTrip", "ChildSafety", "EasyChildPickup"]
  }
}
```

**例**:
- `q1_value = "safety"` → 4つのNeed抽出
  - ChildSafety（子供の安全）
  - DrivingConfidence（運転への自信）
  - AccidentAnxietyReduction（事故不安の軽減）
  - EasyParking（駐車を楽に）

**Need の種類**: 全55種類（v3オントロジー）

---

### **3. Capability マッピング**

Need は さらに **Capability（製品が提供する価値）** に集約:

```
Need → Capability
├─ ChildSafety → SafetyPerformance（安全性能）
├─ DrivingConfidence → SafetyPerformance
├─ FamilyComfort → FamilyFriendly（ファミリー対応）
└─ LowFuelAnxiety → FuelEfficiency（燃費・エネルギー効率）
```

**Capabilityの種類**（9種類）:
1. **SafetyPerformance** - 安全性能
2. **FamilyFriendly** - ファミリー対応
3. **RideComfort** - 快適・静粛性
4. **FuelEfficiency** - 燃費・エネルギー効率
5. **DesignAppeal** - デザイン魅力
6. **SpaceUtility** - 空間・収納
7. **OffRoadCapability** - オフロード・走破性
8. **GeneralPerformance** - 総合性能
9. **TechInnovation** - 先進技術

**マッピングルール**: `config/need-mapping.json` の `need_to_capabilities`

---

### **4. Load（負荷）検出**

特定の回答は **負荷・不安ラベル** も抽出:

```json
{
  "load_labels": {
    "fatigue": "長距離移動による疲労",
    "parking": "駐車・狭い道への不安",
    "maintenance": "維持費への不安",
    "too_much_info": "情報過多による判断負荷"
  }
}
```

**用途**:
1. **Dealer Talk 生成** - 顧客の不安に寄り添ったトークを作成
2. **機能・車種推薦** - Load に対応する機能を持つ車種のスコアをブースト

#### Load → Feature マッピング例

| Load | 推奨される機能 | スコアブースト | 対応 Capability |
|------|--------------|----------------|-----------------|
| **parking** | パノラミックビューモニター、バックモニター、パーキングセンサー、360度カメラ | +18点 | SafetyPerformance |
| **fatigue** | アダプティブクルーズコントロール、Honda SENSING、プレミアムシート | +15点 | RideComfort, SafetyPerformance |
| **maintenance** | ハイブリッドシステム、e:HEV、電動パワートレイン | +15点 | FuelEfficiency |
| **family_dissatisfaction** | 3列シート、スライドドア、後席モニター、広い室内空間 | +16点 | FamilyFriendly, SpaceUtility |

**マッピングルール**: `config/load-feature-mapping.json`

---

## 🚗 車種推薦ロジック

**推薦エンジン**（`engine/recommendation_engine.py`）は以下のロジックで動作:

### **1. マッチングスコア計算**

```python
# ベーススコア: Need/Capability マッチング
base_score = Σ(車種の Capability × 顧客の Need重要度) / 100

# Load ブーストスコア: 負荷に対応する機能の有無
load_boost = Σ(検出された Load に対応する Feature を車種が持つ場合のブーストポイント)

# 最終スコア
final_score = base_score + load_boost

# 例:
# 顧客プロファイル:
#   - Need: SafetyPerformance 重要度高、FamilyFriendly 重要度中
#   - Load: parking（駐車・狭い道への不安）

# 車種A:
#   - SafetyPerformance = 90, FamilyFriendly = 85 → base_score = 87.5
#   - Features: パノラミックビューモニター、バックモニター → load_boost = +18
#   - final_score = 105.5 (上限100で正規化)

# 車種B:
#   - DesignAppeal = 95, OffRoadCapability = 88 → base_score = 40
#   - Features: parking 関連機能なし → load_boost = 0
#   - final_score = 40
```

### **2. Neo4j グラフクエリ**

```cypher
# 顧客の Need → Capability → TechnicalFeature → VehicleModel
MATCH (need:Need)<-[:SUPPORTS]-(cap:Capability)
MATCH (cap)-[:INFLUENCES]->(ec:EvaluationCriteria)
MATCH (tf:TechnicalFeature)-[:REALIZES]->(cap)
MATCH (v:VehicleModel)-[:HAS_FEATURE]->(tf)
WHERE need.name IN $customer_needs
RETURN v.name, COUNT(DISTINCT tf) AS feature_count
ORDER BY feature_count DESC
```

**グラフパス**: Need → Capability → Feature → Vehicle

### **3. フィルタリング**

- ✅ **セグメント適合**（例: 家族重視 → ミニバン優先）
- ✅ **DecisionStyle 適合**（例: 徹底比較派 → 複数候補）
- ✅ **除外ロジック**（例: Premium Luxury → 生活文脈不一致）

### **4. 上位3候補選定**

- スコア順に **トップ3** を選出
- **アーキタイプ**を付与（例: 「安心重視型」「バランス型」）
- **訴求ポイント**を自動生成（例: 「Honda Sensingで運転をサポート」）

---

## 📊 データフロー全体

```
[顧客] 
  ↓ 回答
[Quick Questions (5問)]
  ↓
[DemoProfileCalculator]
  ├→ プロファイルスコア (5軸: safety, family, efficiency, enjoyment, adventure)
  ├→ Need リスト (例: ChildSafety, EfficientDailyMobility)
  ├→ Capability リスト (例: SafetyPerformance, FuelEfficiency)
  └→ Load リスト (例: 駐車不安, 維持費不安)
  ↓
[RecommendationEngine]
  ├→ Neo4j グラフクエリ (Need → Capability → Feature → Vehicle)
  ├→ マッチングスコア計算
  └→ トップ3 + 除外候補
  ↓
[Recommendation 画面]
  ├→ 車種カード × 3 (スコア、アーキタイプ、訴求ポイント)
  └→ 除外理由表示
```

---

## 🔧 実装ファイル

| ファイル | 役割 |
|---------|------|
| `engine/demo_profile.py` | スコア計算・Need/Capabilityマッピング |
| `config/score-weights.json` | 回答→スコア配点ルール |
| `config/need-mapping.json` | 回答→Need、Need→Capabilityマッピング |
| `engine/recommendation_engine.py` | Neo4jクエリ・推薦スコア計算 |
| `api/demo/router.py` | `/answers`, `/recommend` エンドポイント |
| `demo-web/src/components/demo/QuestionsClient.tsx` | フロントエンド質問画面 |

---

## 📈 スコア配点例

### q1_value（最も大切にしたいこと）

| 選択肢 | safety | family | efficiency | enjoyment | adventure |
|--------|--------|--------|------------|-----------|-----------|
| **安全** | +28 | +8 | - | - | - |
| **楽しさ** | - | - | - | +28 | +10 |
| **家族** | +12 | +28 | - | - | - |
| **効率** | +6 | - | +28 | - | - |
| **ステータス** | - | - | +8 | +14 | +18 |

### q4_stress（運転で気になること）

| 選択肢 | safety | family | efficiency | enjoyment | adventure |
|--------|--------|--------|------------|-----------|-----------|
| **疲労** | +18 | +8 | +6 | - | - |
| **渋滞** | +8 | - | +20 | - | - |
| **駐車** | +20 | - | +10 | - | - |
| **操作難** | +22 | - | +8 | - | - |
| **情報過多** | +12 | - | +18 | - | - |

---

## 💡 設計のポイント

| 項目 | 内容 |
|------|------|
| **最小質問数** | 5問で完結（体験時間7-10分を維持） |
| **リアルタイム** | 各回答後すぐにMAPを更新（エンゲージメント向上） |
| **多次元評価** | 1回答が複数軸に影響（複雑な価値観を表現） |
| **時系列重視** | 新しい回答ほど重視（考えが深まる過程を反映） |
| **説明可能性** | スコア→Need→Capability→Featureの経路が追跡可能 |
| **拡張性** | 設定ファイル（JSON）で調整可能（ロジック変更不要） |

---

## 🎯 期待される効果

### 1. **顧客体験**
- ✅ 短時間（5問×30秒＝2.5分）で価値観を可視化
- ✅ MAPで「自分が理解されている」実感
- ✅ 押し付けではなく「納得できる選択」

### 2. **推薦精度**
- ✅ 5軸スコア＋55種類Needで高精度マッチング
- ✅ Neo4jグラフで「なぜその車種か」を説明可能
- ✅ 除外理由も明示（透明性）

### 3. **販売店支援**
- ✅ 顧客インサイト（価値観・不安）を可視化
- ✅ トークスクリプト自動生成（LLM統合）
- ✅ 属人的商談からの脱却

---

## 📚 関連ドキュメント

- [要件定義書](./output/detailed_requirements_specification.md)
- [システム要件](./output/system_requirements.md)
- [Phase 3 完了報告](./design/phase3-completion.md)
- [プロジェクトコンテキスト](../CLAUDE.md)

---

**最終更新**: 2026-05-27  
**作成者**: Development Team
