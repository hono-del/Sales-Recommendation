# 社内サービス案カタログ — 作業ガイド

**対象**: アップグレード / ダウングレードサービス案の整理・ラベル付け担当者  
**作成日**: 2026-05-28  
**所要時間の目安**: 1案あたり 15〜30分（初回は40分程度）  

## まずここから（Excel 担当者向け）

1. **`data/templates/service-offerings-catalog.xlsx`** をコピーする  
   - ファイル名例: `service-offerings_山田太郎.xlsx`
2. **「記入」シート**の **4行目以降**に、1案1行で入力する（3行目は記入例）
3. プルダウンがある列は **リストから選択**（手入力しない）
4. 完了した Excel を共有フォルダ / Teams に提出

詳細な判断基準は本ドキュメントの STEP 2 以降を参照。

---

**関連ファイル**

| ファイル | 用途 |
|----------|------|
| **`data/templates/service-offerings-catalog.xlsx`** | **記入用 Excel（提出形式）** |
| 本ドキュメント | 作業手順・ラベル定義・Need一覧 |
| `config/kg-need-links.json` | 価値観・負荷 → Need の既存マッピング（参照用） |
| `config/service-offerings.json` | 集約後の正本 JSON（集約担当が生成） |
| `scripts/excel_to_service_offerings_json.py` | Excel → JSON 変換（集約担当向け） |

---

## 0. この作業でやること

社内で集めた **アップグレード / ダウングレードのサービス案** を、デモのレコメンド機能で使える形にまとめます。

```
ユーザーの価値観・負荷
    → Need（生活欲求）を抽出        ※既存ロジック
    → Need に紐づくサービスを提案   ※今回整備するカタログ
```

各サービス案には次を付けます。

1. **Need への紐づけ**（レコメンドの主軸）
2. **アップ / ダウン / 横移動** の区分
3. **実在サービスへの模倣**（ユーザーへの説明用）

---

## 1. 納品物

| 誰 | 納品物 | 形式 |
|----|--------|------|
| **各メンバー** | 記入済み Excel | `service-offerings_氏名.xlsx` |
| **集約担当** | マージ済み JSON | `config/service-offerings.json` |

メンバーは **Excel のみ** 提出でOKです。JSON への変換は集約担当が行います。

---

## 2. Excel の構成

| シート | 内容 |
|--------|------|
| **記入** | 1案1行で入力（提出対象） |
| **選択肢** | プルダウン用マスタ（編集不要） |
| **使い方** | 最低限の手順 |

### 記入シートの行の意味

| 行 | 内容 |
|----|------|
| 1行目 | フィールド名（英語・システム用） |
| 2行目 | 日本語ラベル（**※＝必須**） |
| 3行目 | 記入例（削除してOK） |
| **4行目〜** | **ここから入力** |

### 列一覧（記入シート）

| 列 | フィールド | 必須 | 入力方法 |
|----|------------|------|----------|
| A | id | ※ | 手入力（例: `svc_fixed_maintenance`） |
| B | title | ※ | 手入力 |
| C | one_liner | ※ | 手入力 |
| D | direction | ※ | プルダウン |
| E | domain | ※ | プルダウン |
| F | lifecycle | ※ | プルダウン |
| G | status | | プルダウン（未記入なら draft） |
| H | contributor | ※ | 手入力（自分の名前） |
| I | updated_at | | 手入力（例: 2026-05-28） |
| J〜L | primary_need_1〜3 | ※① | プルダウン（①は必須） |
| M〜N | secondary_need_1〜2 | | プルダウン |
| O〜P | load_label_1〜2 | | プルダウン |
| Q〜R | value_axis_1〜2 | | プルダウン |
| S〜T | burden_addressed_1〜2 | | プルダウン（負荷と同じリスト） |
| U〜V | value_shift_1〜2 | | プルダウン |
| W | need_rationale | ※ | 手入力 |
| X | trade_off | ※ | 手入力 |
| Y | analog_name | | 手入力 |
| Z | analog_pattern | | プルダウン |
| AA | analog_why | | 手入力 |
| AB | pitch_template | | 手入力 |
| AC | eligibility | | プルダウン |
| AD | combinability | | プルダウン |
| AE | notes | | 手入力 |

---

## 3. 作業フロー（Excel 版）

```
[STEP 1] Excel テンプレートをコピー
    ↓
[STEP 2] 「記入」シート 4行目〜に入力（プルダウン優先）
    ↓
[STEP 3] チェックリストで自己レビュー
    ↓
[STEP 4] Excel を提出
```

（任意）生案のメモは `notes` 列に書いてOK。別途アイデア票は不要です。

### 集約担当者向け（Excel → JSON）

複数人分の Excel を1つにまとめる場合:

```powershell
cd "C:\Users\a01380\OneDrive - CMC Corporation\デスクトップ\次世代商談"

# 1ファイル目
py scripts/excel_to_service_offerings_json.py "path\to\service-offerings_山田.xlsx"

# 2人目以降は --merge で追記
py scripts/excel_to_service_offerings_json.py "path\to\service-offerings_佐藤.xlsx" --merge
```

テンプレート再生成（列定義を変えたとき）:

```powershell
py scripts/build_service_offerings_excel.py
```

---

## STEP 1（旧・任意）: アイデア票

以下をそのままコピーし、各項目を埋めてください。

```markdown
## サービス案アイデア票

- **案ID（仮）**: svc________________
- **記入者**:
- **記入日**:

### 基本
- **サービス名（仮）**:
- **一言で（20〜40字）**:

### 方向性（どちらか1つ）
- [ ] upgrade（体験・安心・便利が増える／対価も増えがち）
- [ ] downgrade（コスト・機能を抑え、シンプル・十分に寄せる）
- [ ] neutral（横移動・組み替え）

### 困りごと（生活者の言葉で3行以内）


### 実在サービスで似ているもの（あれば）
- **サービス名**:
- **なぜ似ているか**:

### 車・自動車業界で近いもの（あれば）


### メモ・懸念

```

---

## STEP 2: ラベル付け

### 2.1 必須ラベル

| 項目 | 選び方 | 制限 |
|------|--------|------|
| `direction` | `upgrade` / `downgrade` / `neutral` | **1つのみ** |
| `domain` | 下表から **1つ** | サービス領域 |
| `primary_needs` | 付録Aの Need から | **1〜3件**（英語 `name`） |
| `secondary_needs` | 同上 | **0〜2件** |
| `load_labels` | 付録Bから | **0〜2件**（既存デモの負荷ラベル） |
| `need_rationale` | 自由記述 | なぜその Need か（1〜2文） |

#### `domain` 一覧（この中から1つ）

| 値 | 意味 |
|----|------|
| `maintenance` | 点検・整備・消耗品 |
| `connectivity` | コネクテッド・ナビ・アプリ |
| `insurance_warranty` | 保険・延長保証・ロードサービス |
| `ownership_program` | サブスク・リース・定額プラン |
| `upgrade_path` | グレードアップ・オプション追加 |
| `downgrade_path` | プラン見直し・解約・機能オフ |
| `trade_lifecycle` | 下取り・買い替え・乗り換え |
| `concierge_support` | 人による提案・代行・相談 |
| `other` | 上記に当てはまらない |

#### `direction` の判断基準

| 値 | 判断の目安 |
|----|------------|
| `upgrade` | 支払い・コミットは増えがちだが、不安低減・体験向上・手間削減のいずれかが主目的 |
| `downgrade` | 機能・契約を減らすが、TCO最適化・判断の簡素化・「十分でいい」が主目的 |
| `neutral` | コスト帯は大きく変えず、中身の組み替え |

---

### 2.2 推奨ラベル（できるだけ埋める）

| 項目 | 選び方 |
|------|--------|
| `value_axes` | `safety` / `family` / `efficiency` / `enjoyment` / `adventure` から **0〜2件** |
| `burden_addressed` | 付録Bと同じ文言で、サービスが軽減する負荷 |
| `value_shift` | 下表から **1〜2件** |
| `lifecycle` | `pre_purchase` / `ownership` / `renewal` / `exit` から1件 |
| `trade_off` | トレードオフを1文（例:「月額は増えるが、突発支出の不安が減る」） |
| `analog` | 実在サービス模倣（下記） |

#### `value_shift` 一覧

| 値 | 意味 |
|----|------|
| `cost_down` | 支出・TCOを下げる |
| `risk_down` | 不安・リスクを下げる |
| `convenience_up` | 手間・時間を減らす |
| `prestige_up` | 上質感・ステータスを上げる |
| `control_up` | 自分でコントロールできる感を上げる |
| `simplicity_up` | 選択肢・判断を減らす |

#### 実在サービス模倣 `analog`（説明・画面コピー用）

| フィールド | 内容 |
|------------|------|
| `name` | 実在サービス名（例: 携帯の定額プラン、Amazon 定期おトク便） |
| `pattern` | 下表から1つ |
| `why` | なぜこの型を真似するか（1文） |
| `pitch_template` | ユーザー向け例文（例:「〇〇のように、△△をシンプルに」） |

#### `analog.pattern` 一覧

| 値 | 意味 | 例 |
|----|------|-----|
| `predictable_cost` | 変動費を固定化 | 定額メンテ、サブスク |
| `good_enough_bundle` | 必要十分のパッケージ | おすすめ3点セット |
| `tier_change` | プラン段階の上下 | 携帯プラン見直し |
| `expert_curated` | 専門家・スタッフおまかせ | コンシェルジュ |
| `self_serve_compare` | 自分で比較して選ぶ | 比較サイト型 |
| `usage_based` | 使った分だけ | 従量課金 |
| `insurance_wrapper` | リスクを包む | 延長保証、ロードサービス |
| `loyalty_retention` | 継続・囲い込み | メンバーシップ |
| `other` | 上記以外 | — |

> **注意**: `analog` は説明用です。レコメンドの主因は **Need（`primary_needs`）** にしてください。

---

### 2.3 Need の付け方（重要）

**機能名ではなく「どの生活欲求が満たされるか」で選ぶ。**

| 良い例 | 悪い例 |
|--------|--------|
| 定額メンテ → `MaintenanceCostReduction` | 「Honda Sensing」だけでタグ付け |
| 乗換サポート → `ResaleValueRetention` + `EfficientDailyMobility` | 自由タグ `#お得` `#安心` |

**重みの目安**

| 種別 | weight |
|------|--------|
| 主 Need（`primary_needs`） | `1.0` |
| 副 Need（`secondary_needs`） | `0.5` |

同じ Need に対して `upgrade` と `downgrade` の両方があるのは問題ありません。

---

## STEP 3: 提出前チェックリスト（Excel）

- [ ] 4行目以降に入力している（3行目の記入例は残っていても可。`id` が `svc_example` の行は変換時に無視されます）
- [ ] 必須列（※）が空でない
- [ ] `primary_need_1` が選ばれている
- [ ] `direction` / `domain` / `lifecycle` がプルダウンから選択されている
- [ ] `load_label` はプルダウンから選択（文言の打ち間違い防止）
- [ ] `need_rationale` / `trade_off` が1文以上ある
- [ ] `id` は英小文字・数字・アンダースコアのみ
- [ ] 車の機能名だけで Need を選んでいない
- [ ] ファイル名に担当者名が入っている（例: `service-offerings_山田太郎.xlsx`）

### 参考: 集約後の JSON 形式

メンバーは JSON を直接編集しません。Excel は次のような構造に変換されます。

```json
{
  "id": "svc_fixed_maintenance",
  "title": "定額メンテナンスプラン",
  "primary_needs": [{ "name": "MaintenanceCostReduction", "weight": 1.0 }],
  "direction": "upgrade",
  "domain": "maintenance"
}
```

---

## 集約時の重複チェック（担当者向け）

### 重複の目安（統合を検討）

次がすべて近い場合は、担当者間で統合を相談:

- 同じ `direction`
- 同じ `primary_needs[0].name`
- 同じ `analog.pattern`

---

## 付録A: Need 一覧（55種）

`name` を Excel の Need プルダウンから選んでください。`label` は選定時の参考です。

### Family

| name | label |
|------|-------|
| ChildSafety | 子供を安全に乗せたい |
| EasyChildPickup | 子供の乗せ降ろしを楽にしたい |
| FamilyConversation | 家族で会話しやすい空間が欲しい |
| FamilyComfort | 家族全員が快適に移動したい |
| LargeCargoForFamily | ベビーカーや荷物を楽に積みたい |
| WeekendFamilyTrip | 家族旅行を楽しみたい |
| ChildMonitoringEase | 後席の子供の様子を確認したい |
| StressFreeSchoolPickup | 送迎のストレスを減らしたい |
| PetFriendlyTravel | ペットと快適に移動したい |

### Safety

| name | label |
|------|-------|
| EasyParking | 駐車を楽にしたい |
| VisibilityConfidence | 周囲を見やすくしたい |
| DrivingConfidence | 運転への不安を減らしたい |
| AccidentAnxietyReduction | 事故不安を減らしたい |
| NightDrivingConfidence | 夜間運転を安心したい |
| SnowDrivingConfidence | 雪道でも安心したい |
| BeginnerFriendlyDriving | 運転初心者でも扱いやすくしたい |
| ElderlyDrivingSupport | 高齢でも安全に運転したい |

### Comfort

| name | label |
|------|-------|
| FatigueReduction | 長時間運転で疲れたくない |
| QuietCabinExperience | 静かな空間で移動したい |
| SmoothRideComfort | 乗り心地を良くしたい |
| StressFreeCommute | 通勤ストレスを減らしたい |
| RelaxingDrive | リラックスして運転したい |
| ComfortableLongDistanceTravel | 長距離移動を快適にしたい |
| ClimateComfort | 車内温度を快適に保ちたい |

### Cargo

| name | label |
|------|-------|
| FlexibleCargoSpace | 荷物量に柔軟対応したい |
| OutdoorGearTransport | アウトドア用品を積みたい |
| EasyLoading | 荷物を積み下ろししやすくしたい |
| LargeShoppingCapacity | まとめ買いに対応したい |
| SportsEquipmentTransport | スポーツ用品を運びたい |
| FlatSeatUtility | 車中泊や大きな荷物に対応したい |

### Economy

| name | label |
|------|-------|
| LowFuelAnxiety | 燃料代不安を減らしたい |
| MaintenanceCostReduction | 維持費を抑えたい |
| LongTermReliability | 長く安心して乗りたい |
| ResaleValueRetention | リセール価値を維持したい |
| EfficientDailyMobility | 日常移動コストを抑えたい |

### Lifestyle

| name | label |
|------|-------|
| DrivingEnjoyment | 運転そのものを楽しみたい |
| AdventureLifestyle | 冒険感を楽しみたい |
| OutdoorLifestyle | アウトドア生活を楽しみたい |
| EmotionalAttachment | 愛着を持てる車に乗りたい |
| PersonalExpression | 自分らしさを表現したい |
| PremiumFeeling | 上質感を感じたい |
| ExcitingAcceleration | 加速感を楽しみたい |
| StatusRecognition | 周囲から良く見られたい |

### Urban

| name | label |
|------|-------|
| UrbanManeuverability | 狭い道でも扱いやすくしたい |
| CompactParkingEase | 小さい駐車場でも停めやすくしたい |
| ShortTripEfficiency | 短距離移動を効率化したい |
| QuickErrandMobility | ちょっとした移動を楽にしたい |

### Accessibility

| name | label |
|------|-------|
| EasyEntryExit | 乗り降りを楽にしたい |
| LowPhysicalBurden | 身体負担を減らしたい |
| AccessibleSeating | 座りやすい姿勢を確保したい |
| CaregiverSupport | 介護・送迎を楽にしたい |

### EV

| name | label |
|------|-------|
| EnvironmentalResponsibility | 環境配慮したい |
| ChargingConfidence | 充電不安を減らしたい |
| QuietElectricExperience | EVの静かさを楽しみたい |
| EnergyEfficiency | エネルギー効率を高めたい |

---

## 付録B: 負荷ラベル一覧（`load_labels` 用）

`config/kg-need-links.json` と同じ文言を使ってください。**コピペ推奨。**

| load_label |
|------------|
| 長距離移動による疲労 |
| 渋滞ストレス |
| 駐車・狭い道への不安 |
| 操作の難しさ |
| 情報過多による判断負荷 |
| 家族同乗時の不満リスク |
| 維持費への不安 |
| 機能不足による後悔 |
| 使わない設備への投資 |
| すぐ飽きるリスク |

---

## 付録C: 価値観5軸（`value_axes` 用）

| 値 | 意味 |
|----|------|
| `safety` | 安心・安全 |
| `family` | 家族 |
| `efficiency` | 効率・コスト |
| `enjoyment` | 楽しさ・体験 |
| `adventure` | 冒険・アウトドア |

---

---

## 付録D: Google スプレッドシートで使う場合

Excel テンプレートを Google ドライブにアップロードして共有可能です。  
プルダウン（データの入力規則）はそのまま使えますが、**提出時は Excel (.xlsx) でダウンロード**して共有してください。

---

## FAQ

**Q. Need がどれもしっくりこない**  
A. 最も近い1件を `primary_needs` に入れ、`need_rationale` に「近似理由」を書いてください。新しい Need は追加しません（55種固定）。

**Q. アップとダウンどちらか迷う**  
A. ユーザーにとっての主効果で決めてください。同じ案を2レコードに分けないでください。

**Q. 実在サービスが思いつかない**  
A. `analog.pattern` だけ選び、`analog.name` は `"（社内オリジナル）"` と記載可。

**Q. 何件まで書けばよいか**  
A. 担当範囲はリーダーと相談。品質優先で、1人あたり5〜10件の正規化を目安にしてください。

---

## 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-05-28 | 初版作成 |
| 2026-05-28 | Excel テンプレート形式に変更 |
