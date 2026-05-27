# Decision Intelligence PoC — プロジェクトコンテキスト (v3)

## このプロジェクトの概要

Honda の購入者レビュー **4,205件** を LLM で構造化し、Neo4j ナレッジグラフに格納した意思決定分析システム。

---

## テストセッションでの役割

このセッションは **チャットテスター** として動作する。
ユーザーの質問に対して：
1. 適切な Cypher クエリを組み立て Neo4j に問い合わせる
2. 結果を日本語でわかりやすく回答する
3. 必要に応じて複数クエリを組み合わせて深掘りする

---

## Neo4j 接続情報

```powershell
# クエリ実行コマンド（PowerShell）
# Neo4j Desktop（Local instance: Recommendation）
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="recommendation"
```

- URI: bolt://localhost:7687（Neo4j Desktop: Recommendation）
- User: neo4j / Password: recommendation

**注意**: Aura Cloud (neo4j+s://25257eca.databases.neo4j.io) は企業ネットワークでポート 7687 がブロックされているため使用不可。

---

## グラフスキーマ v3（ノード 13種類）

### Consumer（4,205件）
購入者本人。主なプロパティ：
- `id` — story_id
- `gender` — 性別
- `age_group` — 年代
- `location` — 都道府県
- `family_size` — 家族人数
- `children` — 子供人数
- `children_ages` — 子供年齢層リスト（infant/elementary/middle_high/adult）
- `marital_status` — married/single/unknown
- `household_type` — single/couple/nuclear/extended/unknown
- `has_elderly` — 高齢者同居 true/false/null
- `household_vehicle_count` — 世帯保有台数（ルールベース抽出、nullあり）

### DecisionStyle（6種類）
- name: Maximizer/Satisficer/Authority-driven/Delegator/Intuitive/Impulsive
- label: 徹底比較型/十分型/権威依存型/委任型/直感型/衝動型
- `decision_behavior` — 意思決定行動パターンリスト（配列）
- `information_preference` — 刺さる情報タイプリスト（配列）

### LifeEvent（9種類）
- name: child_birth/marriage/relocation/job_change/retirement/child_school/home_purchase/independence/family_growth

### Trigger（9種類）
- name: vehicle_aging/inspection/accident/maintenance_cost/new_model_release/promotion/test_drive/lifestyle_change/other

### Need（55種類）— 生活欲求型 v3
- `name` — 英語コード（例: ChildSafety, SmoothRideComfort）
- `label` — 日本語の生活欲求（例: 「子供を安全に乗せたい」「乗り心地を良くしたい」）
- `group` — グループ（Family/Safety/Comfort/Cargo/Economy/Lifestyle/Urban/Accessibility/EV）

| group | name（一部） | label |
|-------|-------------|-------|
| Family | ChildSafety / EasyChildPickup / FamilyComfort / WeekendFamilyTrip ... | 子供を安全に乗せたい / 子供の乗せ降ろしを楽に... |
| Safety | EasyParking / DrivingConfidence / AccidentAnxietyReduction / SnowDrivingConfidence ... | 駐車を楽にしたい / 運転への不安を減らしたい... |
| Comfort | SmoothRideComfort / QuietCabinExperience / FatigueReduction / RelaxingDrive ... | 乗り心地を良くしたい / 静かな空間で移動したい... |
| Cargo | FlexibleCargoSpace / OutdoorGearTransport / FlatSeatUtility ... | 荷物量に柔軟対応したい / アウトドア用品を積みたい... |
| Economy | LowFuelAnxiety / MaintenanceCostReduction / LongTermReliability ... | 燃料代不安を減らしたい / 維持費を抑えたい... |
| Lifestyle | DrivingEnjoyment / OutdoorLifestyle / EmotionalAttachment / PremiumFeeling ... | 運転そのものを楽しみたい / 愛着を持てる車に乗りたい... |
| Urban | UrbanManeuverability / CompactParkingEase / ShortTripEfficiency ... | 狭い道でも扱いやすくしたい / 短距離移動を効率化したい... |
| Accessibility | EasyEntryExit / LowPhysicalBurden / CaregiverSupport ... | 乗り降りを楽にしたい / 介護・送迎を楽にしたい... |
| EV | EnvironmentalResponsibility / ChargingConfidence / QuietElectricExperience ... | 環境配慮したい / 充電不安を減らしたい... |

全55件は `graph/graph_builder.py` の `NEW_NEED_MASTER` を参照。

### EvaluationCriteria（5,046件）
購入者ごとの自由記述評価基準
- `name` — テキスト（例: 「燃費の良さ」「室内の広さ」）
- `label` — Capability分類（SafetyPerformance/FuelEfficiency/DesignAppeal/TechInnovation/SpaceUtility/RideComfort/FamilyFriendly/OffRoadCapability/GeneralPerformance）

### PurchaseDriver（11種類）
最終決め手の類型
- `name` — 日本語（例: 安全性能、燃費・維持費）
- `label` — 英語コード（例: safety_performance、fuel_economy）

### VehicleModel（3,817件）
- `name` — 車種名（例: FIT, ステップワゴン）
- `brand` — ブランド名
- `segment` — セグメント（B_Segment/C_Segment/Kei_Segment/CompactSUV/LargeMinivan など）
- `body_type` — ボディタイプ（Hatchback/Sedan/Minivan/SUV/KeiCar など）
- `fuel_type` — 燃料種別（Gasoline/Hybrid/Electric）
- `drive_type` — 駆動方式（FWD/4WD/AWD/FR/MR/RWD）
- `seating_capacity` — 定員数
- `category` — カテゴリ（Passenger/Commercial/Performance/Luxury/Electrified/Utility）

### TechnicalFeature（411件）
Honda の製品の具体的な機能・技術仕様（旧 Feature ノード）
- `name` — 機能名（日本語テキスト）
- `category` — 分類（safety/fuel_efficiency/design/technology/space/comfort/family/offroad/general）

### Capability（9種類）【v3新規】
製品が提供する価値・能力の抽象レベルの分類
- name: SafetyPerformance/FuelEfficiency/DesignAppeal/TechInnovation/SpaceUtility/RideComfort/FamilyFriendly/OffRoadCapability/GeneralPerformance
- `label` — 日本語（安全性能/燃費・エネルギー効率/デザイン魅力/先進技術/空間・収納/快適・静粛性/ファミリー対応/オフロード・走破性/総合性能）

### VehicleOwnership（7,533件）
購入インスタンス（Consumer 1人につき現在車＋前所有車）
- `id` — {story_id}_current / {story_id}_prev
- `is_current` — true（今回購入）/ false（前所有車）
- `purchase_year` — 購入年
- `model_year` — 車の年式
- `satisfaction_score` — 満足度（1-5）
- `grade` — グレード（RS/G/EX など）
- `body_color` — ボディカラー
- `interior_color` — インテリアカラー
- `optional_equipment` — オプション装備リスト
- `usage_pattern` — 使用用途
- `annual_mileage` — 年間走行距離
- `vehicle_role` — 車の役割リスト（FamilyVehicle/CommuteVehicle/HobbyVehicle/BusinessVehicle/OutdoorVehicle/CityVehicle/PrimaryVehicle/SecondaryVehicle など）

### Outcome（4,085件）
購入後の結果・感想テキスト
- `name` — テキスト
- `label` — Satisfied/Neutral/Dissatisfied/Unknown（satisfaction_scoreから導出）

### Regret（14種類）
- name: fuel_cost/cargo_space/ride_quality/size_too_large/size_too_small/price/maintenance/design/technology/other

---

## リレーションシップ一覧 v3

```
Consumer -[HAS_DECISION_STYLE]-> DecisionStyle
Consumer -[EXPERIENCED]-> LifeEvent
Consumer -[HAS_TRIGGER]-> Trigger
Consumer -[HAS_NEED]-> Need
Need -[HAS_SUB_NEED]-> Need
Consumer -[VALUED]-> EvaluationCriteria
Consumer -[DECIDED]-> PurchaseDriver
Consumer -[CONSIDERED]-> VehicleModel
Consumer -[OWNED]-> VehicleOwnership          ※ own.decision_weight (1.0=現在車, 0.5=前所有車)
VehicleOwnership -[OF_MODEL]-> VehicleModel
VehicleOwnership -[RESULTED_IN]-> Outcome     ※ ri.score, ri.description, ri.timing
VehicleOwnership -[CAUSED_REGRET]-> Regret    ※ cr.description, cr.severity(1-3), cr.timing
VehicleModel -[HAS_FEATURE]-> TechnicalFeature
TechnicalFeature -[REALIZES]-> Capability
Capability -[SUPPORTS]-> Need
Capability -[INFLUENCES]-> EvaluationCriteria
Capability -[REDUCES]-> Regret
Capability -[APPEALS_TO]-> DecisionStyle
```

### v2→v3 で削除されたリレーション
```
Consumer -[SELECTED]-> VehicleModel          → OWNED に統合
Consumer -[HAS_OUTCOME]-> Outcome            → VehicleOwnership -[RESULTED_IN]->
Consumer -[HAS_REGRET]-> Regret              → VehicleOwnership -[CAUSED_REGRET]->
EvaluationCriteria -[MAPS_TO]-> Feature      → Capability -[INFLUENCES]->
VehicleModel -[MEETS]-> EvaluationCriteria   → 削除
Feature -[SATISFIES]-> Need                  → Capability -[SUPPORTS]->
```

---

## よく使う Cypher パターン v3

### 車種別の購入者数（v3: OWNED経由）
```cypher
MATCH (c:Consumer)-[own:OWNED {decision_weight: 1.0}]->(vo:VehicleOwnership)-[:OF_MODEL]->(v:VehicleModel)
RETURN v.name AS model, count(c) AS cnt
ORDER BY cnt DESC LIMIT 10
```

### 特定車種を選んだ人の DecisionStyle 分布
```cypher
MATCH (c:Consumer)-[:OWNED]->(vo:VehicleOwnership {is_current: true})-[:OF_MODEL]->(v:VehicleModel {name: 'FIT'})
MATCH (c)-[:HAS_DECISION_STYLE]->(d:DecisionStyle)
RETURN d.label AS style, count(*) AS cnt
ORDER BY cnt DESC
```

### LifeEvent × 車種のクロス集計
```cypher
MATCH (c:Consumer)-[:EXPERIENCED]->(le:LifeEvent)
MATCH (c)-[:OWNED]->(vo:VehicleOwnership {is_current: true})-[:OF_MODEL]->(v:VehicleModel)
RETURN le.label AS event, v.name AS model, count(*) AS cnt
ORDER BY cnt DESC LIMIT 20
```

### 後悔している人の特徴（v3: CAUSED_REGRET）
```cypher
MATCH (vo:VehicleOwnership {is_current: true})-[cr:CAUSED_REGRET]->(r:Regret)
MATCH (c:Consumer)-[:OWNED]->(vo)
RETURN r.label AS regret, count(*) AS cnt,
       avg(vo.satisfaction_score) AS avg_score
ORDER BY cnt DESC
```

### Capability が支持する DecisionStyle
```cypher
MATCH (cap:Capability)-[:APPEALS_TO]->(d:DecisionStyle)
RETURN cap.label AS capability, collect(d.label) AS styles
```

### 特定 Capability に関心を持つ消費者のプロファイル
```cypher
MATCH (cap:Capability {name: 'SafetyPerformance'})-[:INFLUENCES]->(ec:EvaluationCriteria)
MATCH (c:Consumer)-[:VALUED]->(ec)
RETURN c.age_group AS age, c.household_type AS household,
       count(c) AS cnt ORDER BY cnt DESC LIMIT 10
```

### vehicle_role 別の車種
```cypher
MATCH (vo:VehicleOwnership)-[:OF_MODEL]->(v:VehicleModel)
WHERE 'FamilyVehicle' IN vo.vehicle_role AND vo.is_current = true
RETURN v.name AS model, count(*) AS cnt ORDER BY cnt DESC LIMIT 10
```

### Outcome 満足度分布
```cypher
MATCH (vo:VehicleOwnership {is_current: true})-[ri:RESULTED_IN]->(o:Outcome)
RETURN o.label AS satisfaction, count(*) AS cnt, avg(ri.score) AS avg_score
ORDER BY cnt DESC
```

---

## 回答スタイルのガイドライン

- 数値は具体的に（「多い」ではなく「X人（X%）」）
- 上位3〜5件を中心に説明
- 興味深いインサイトがあれば追加で深掘りクエリを提案
- クエリに問題があれば修正して再実行
- 「データに記録されていない」場合はその旨を明示

---

## ファイル構成

```
decision-intelligence-poc/
├── data/
│   ├── raw/consumer_stories.json          # 元データ（4,205件）
│   └── processed/
│       ├── consumer_decisions.json         # 抽出済み構造化データ
│       └── product_features.json           # 製品機能データ
├── extractor/
│   ├── consumer_extractor.py              # LLM抽出（逐次）
│   ├── rule_based_extractor.py            # ルールベース抽出
│   └── batch_llm_extractor.py             # Batch API（50%割引）
├── graph/
│   ├── graph_builder.py                   # ★ グラフ構築 v3（全ルール定義含む）
│   ├── update_ontology_v3_step1.py        # Step1: DecisionStyle/VehicleOwnership/VehicleModel
│   ├── update_ontology_v3_step3.py        # Step3: Feature→TechnicalFeature+Capability分割
│   └── update_ontology_v3_step4.py        # Step4: Need/PurchaseDriver/EC label追加
└── CLAUDE.md                              # このファイル
```

## 再構築手順（v3オントロジー）

```powershell
# 1. 抽出（ルールベース）
cd "C:\Users\a01380\OneDrive - CMC Corporation\デスクトップ\次世代商談"
py rule_based_extractor.py

# 2. decision_style + regret のみ LLM（Batch API）
py batch_llm_extractor.py
# 完了後:
py batch_llm_extractor.py --poll

# 3. グラフ構築（v3ルール全適用）
$env:NEO4J_PASSWORD="KMixerOrigin2026"
py graph_builder.py
```
