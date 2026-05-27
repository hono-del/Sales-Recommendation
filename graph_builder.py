"""
Knowledge Graph Builder v3 — Extended Ontology

ノード (13種類):
  Consumer, DecisionStyle, LifeEvent, Trigger,
  Need, EvaluationCriteria, PurchaseDriver,
  VehicleModel, TechnicalFeature, Capability,
  VehicleOwnership, Outcome, Regret

リレーション (Consumer側):
  HAS_DECISION_STYLE, EXPERIENCED, HAS_TRIGGER,
  HAS_NEED, VALUED, DECIDED, CONSIDERED, OWNED

リレーション (VehicleOwnership側):
  OF_MODEL, RESULTED_IN, CAUSED_REGRET

リレーション (Product側):
  HAS_FEATURE, REALIZES, SUPPORTS, INFLUENCES, REDUCES, APPEALS_TO

リレーション (Need側):
  HAS_SUB_NEED

変更履歴:
  v2 → v3:
  - Feature を TechnicalFeature + Capability に分割
  - Consumer -[SELECTED]->  削除 → OWNED.decision_weight で代替
  - Consumer -[HAS_OUTCOME]-> 削除 → VehicleOwnership -[RESULTED_IN]->
  - Consumer -[HAS_REGRET]->  削除 → VehicleOwnership -[CAUSED_REGRET]->
  - EvaluationCriteria -[MAPS_TO]-> Feature 削除 → Capability -[INFLUENCES]->
  - VehicleModel -[MEETS]-> EvaluationCriteria 削除
  - Feature -[SATISFIES]-> Need 削除 → Capability -[SUPPORTS]->
  - DecisionStyle に decision_behavior / information_preference 追加
  - Need に label 追加
  - PurchaseDriver に label 追加
  - EvaluationCriteria に label 追加
  - VehicleOwnership に vehicle_role 追加
  - VehicleModel に segment / body_type / fuel_type / drive_type / seating_capacity 追加
  - Consumer に household_vehicle_count 追加
"""
import json
import os
import re
from pathlib import Path
from neo4j import GraphDatabase

NEO4J_URI      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

CONSUMER_DECISIONS_PATH = Path("data/processed/consumer_decisions.json")
PRODUCT_FEATURES_PATH   = Path("data/processed/product_features.json")
CONSUMER_STORIES_PATH   = Path("data/raw/consumer_stories.json")

# =============================================================================
# ── マスタデータ / ルール定義 ─────────────────────────────────────────────────
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# [RULE-GENDER] 性別バリデーション
# ─────────────────────────────────────────────────────────────────────────────
_VALID_GENDERS = {"男性", "女性", "その他", "男", "女"}

def _clean_gender(value: str) -> str:
    if not value:
        return ""
    return value if value in _VALID_GENDERS else ""


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-DECISION-STYLE] DecisionStyle マスタ
# ─────────────────────────────────────────────────────────────────────────────
DECISION_STYLE_MASTER = {
    "Maximizer": {
        "label":       "徹底比較型",
        "description": "複数モデルを徹底的に比較・スペック重視",
        "decision_behavior": [
            "compares_many_options", "seeks_best_choice", "avoids_regret",
            "long_decision_cycle", "research_driven", "sensitive_to_tradeoffs",
        ],
        "information_preference": [
            "comparison_table", "detailed_specification", "expert_review",
            "ranking", "ownership_cost_analysis", "competitive_comparison",
            "long_term_reliability_data",
        ],
    },
    "Satisficer": {
        "label":       "十分型",
        "description": "一定基準を満たしたら決定する十分満足型",
        "decision_behavior": [
            "sets_acceptance_threshold", "limits_option_comparison",
            "prioritizes_efficiency", "prefers_low_cognitive_load",
            "shortlist_oriented",
        ],
        "information_preference": [
            "recommended_package", "simple_comparison", "best_value_summary",
            "easy_to_understand_explanation", "popular_choice",
            "time_saving_information",
        ],
    },
    "Authority-driven": {
        "label":       "権威依存型",
        "description": "営業・家族・友人・ブランドの意見に従う",
        "decision_behavior": [
            "trusts_experts", "follows_authoritative_opinion",
            "brand_reassurance_seeking", "risk_avoidant",
            "validates_with_external_authority",
        ],
        "information_preference": [
            "expert_opinion", "dealer_recommendation", "brand_history",
            "safety_awards", "professional_review", "certification",
            "customer_satisfaction_ranking",
        ],
    },
    "Delegator": {
        "label":       "委任型",
        "description": "意思決定を他者に委ねる",
        "decision_behavior": [
            "relies_on_recommendation", "outsources_evaluation",
            "avoids_detailed_analysis", "seeks_social_consensus",
            "decision_by_trusted_person",
        ],
        "information_preference": [
            "recommended_choice", "staff_pick", "family_feedback",
            "friend_usage_story", "popular_configuration", "best_seller",
            "easy_recommendation",
        ],
    },
    "Intuitive": {
        "label":       "直感型",
        "description": "フィーリング・一目惚れで決める直感型",
        "decision_behavior": [
            "relies_on_feeling", "emotionally_driven",
            "instant_impression_sensitive", "experience_oriented",
            "visual_emphasis",
        ],
        "information_preference": [
            "visual_design", "test_drive_experience", "storytelling",
            "lifestyle_imagery", "emotional_message", "video_content",
            "owner_story",
        ],
    },
    "Impulsive": {
        "label":       "衝動型",
        "description": "勢い・その場の雰囲気で即決する衝動型",
        "decision_behavior": [
            "fast_decision", "emotionally_reactive", "promotion_sensitive",
            "novelty_seeking", "low_deliberation",
        ],
        "information_preference": [
            "limited_offer", "discount_information", "immediate_availability",
            "campaign_message", "attention_grabbing_visual", "social_trend",
            "quick_summary",
        ],
    },
}

DECISION_STYLE_LABELS = {k: v["label"] for k, v in DECISION_STYLE_MASTER.items()}
DECISION_STYLE_DESCRIPTIONS = {k: v.get("description", "") for k, v in DECISION_STYLE_MASTER.items()}

# ─────────────────────────────────────────────────────────────────────────────
# [RULE-LIFE-EVENT] LifeEvent マスタ
# ─────────────────────────────────────────────────────────────────────────────
LIFE_EVENT_LABELS = {
    "child_birth":   "子供誕生",
    "marriage":      "結婚",
    "relocation":    "引越し・転勤",
    "job_change":    "転職・就職",
    "retirement":    "定年退職",
    "child_school":  "子供の入学・進学",
    "home_purchase": "マイホーム購入",
    "independence":  "独立・一人暮らし",
    "family_growth": "家族の増加（その他）",
}

_KIKKAKE_TO_LIFE_EVENT: dict[str, list[str]] = {
    "child_birth":   ["生まれ", "出産", "赤ちゃん", "誕生", "妊娠"],
    "marriage":      ["結婚", "新婚", "入籍"],
    "relocation":    ["引越", "転勤", "転居"],
    "job_change":    ["転職", "就職", "異動"],
    "retirement":    ["定年", "引退", "リタイア"],
    "child_school":  ["入学", "進学", "小学", "中学", "高校"],
    "home_purchase": ["マイホーム", "一戸建て", "新居"],
    "independence":  ["独立", "一人暮らし"],
}

def _kikkake_to_life_event(text: str) -> str | None:
    for cat, kws in _KIKKAKE_TO_LIFE_EVENT.items():
        if any(kw in text for kw in kws):
            return cat
    return None


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-TRIGGER] Trigger マスタ
# ─────────────────────────────────────────────────────────────────────────────
TRIGGER_LABELS = {
    "vehicle_aging":     "車の老朽化",
    "inspection":        "車検",
    "accident":          "事故・故障",
    "maintenance_cost":  "維持費増加",
    "new_model_release": "新型モデル発売",
    "promotion":         "キャンペーン・値引き",
    "test_drive":        "試乗・口コミ",
    "lifestyle_change":  "ライフスタイル変化",
    "other":             "その他",
}

_KIKKAKE_TO_TRIGGER: dict[str, list[str]] = {
    "vehicle_aging":     ["古くなった", "壊れ", "故障", "年数", "走行距離", "ガタが", "傷んで"],
    "inspection":        ["車検"],
    "accident":          ["事故", "ぶつけ", "衝突", "追突"],
    "maintenance_cost":  ["維持費", "修理費", "燃費が悪", "ガソリン代が"],
    "new_model_release": ["新型", "フルモデル", "モデルチェンジ", "新発売"],
    "promotion":         ["キャンペーン", "特典", "値引き", "セール"],
    "test_drive":        ["試乗", "口コミ", "友人に勧め", "SNS で"],
    "lifestyle_change":  ["趣味", "アウトドア", "キャンプ", "ライフスタイル", "独立"],
}

def _kikkake_to_trigger(text: str) -> str:
    for cat, kws in _KIKKAKE_TO_TRIGGER.items():
        if any(kw in text for kw in kws):
            return cat
    return "other"


def _categorize_sub_trigger(text: str) -> str:
    """後方互換: きっかけテキストからトリガー種別を返す"""
    return _kikkake_to_trigger(text)


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-NEED] Need マスタ v3 — 生活欲求型（55件）
# ─────────────────────────────────────────────────────────────────────────────
NEW_NEED_MASTER = [
    # Family
    {"name": "ChildSafety",            "label": "子供を安全に乗せたい",            "group": "Family"},
    {"name": "EasyChildPickup",        "label": "子供の乗せ降ろしを楽にしたい",    "group": "Family"},
    {"name": "FamilyConversation",     "label": "家族で会話しやすい空間が欲しい",  "group": "Family"},
    {"name": "FamilyComfort",          "label": "家族全員が快適に移動したい",      "group": "Family"},
    {"name": "LargeCargoForFamily",    "label": "ベビーカーや荷物を楽に積みたい", "group": "Family"},
    {"name": "WeekendFamilyTrip",      "label": "家族旅行を楽しみたい",           "group": "Family"},
    {"name": "ChildMonitoringEase",    "label": "後席の子供の様子を確認したい",    "group": "Family"},
    {"name": "StressFreeSchoolPickup", "label": "送迎のストレスを減らしたい",      "group": "Family"},
    {"name": "PetFriendlyTravel",      "label": "ペットと快適に移動したい",        "group": "Family"},
    # Safety
    {"name": "EasyParking",              "label": "駐車を楽にしたい",              "group": "Safety"},
    {"name": "VisibilityConfidence",     "label": "周囲を見やすくしたい",          "group": "Safety"},
    {"name": "DrivingConfidence",        "label": "運転への不安を減らしたい",      "group": "Safety"},
    {"name": "AccidentAnxietyReduction", "label": "事故不安を減らしたい",          "group": "Safety"},
    {"name": "NightDrivingConfidence",   "label": "夜間運転を安心したい",          "group": "Safety"},
    {"name": "SnowDrivingConfidence",    "label": "雪道でも安心したい",            "group": "Safety"},
    {"name": "BeginnerFriendlyDriving", "label": "運転初心者でも扱いやすくしたい", "group": "Safety"},
    {"name": "ElderlyDrivingSupport",    "label": "高齢でも安全に運転したい",      "group": "Safety"},
    # Comfort
    {"name": "FatigueReduction",              "label": "長時間運転で疲れたくない",    "group": "Comfort"},
    {"name": "QuietCabinExperience",          "label": "静かな空間で移動したい",      "group": "Comfort"},
    {"name": "SmoothRideComfort",             "label": "乗り心地を良くしたい",        "group": "Comfort"},
    {"name": "StressFreeCommute",             "label": "通勤ストレスを減らしたい",    "group": "Comfort"},
    {"name": "RelaxingDrive",                 "label": "リラックスして運転したい",    "group": "Comfort"},
    {"name": "ComfortableLongDistanceTravel", "label": "長距離移動を快適にしたい",    "group": "Comfort"},
    {"name": "ClimateComfort",                "label": "車内温度を快適に保ちたい",    "group": "Comfort"},
    # Cargo
    {"name": "FlexibleCargoSpace",       "label": "荷物量に柔軟対応したい",           "group": "Cargo"},
    {"name": "OutdoorGearTransport",     "label": "アウトドア用品を積みたい",         "group": "Cargo"},
    {"name": "EasyLoading",              "label": "荷物を積み下ろししやすくしたい",   "group": "Cargo"},
    {"name": "LargeShoppingCapacity",    "label": "まとめ買いに対応したい",           "group": "Cargo"},
    {"name": "SportsEquipmentTransport", "label": "スポーツ用品を運びたい",           "group": "Cargo"},
    {"name": "FlatSeatUtility",          "label": "車中泊や大きな荷物に対応したい",   "group": "Cargo"},
    # Economy
    {"name": "LowFuelAnxiety",           "label": "燃料代不安を減らしたい",          "group": "Economy"},
    {"name": "MaintenanceCostReduction", "label": "維持費を抑えたい",                "group": "Economy"},
    {"name": "LongTermReliability",      "label": "長く安心して乗りたい",            "group": "Economy"},
    {"name": "ResaleValueRetention",     "label": "リセール価値を維持したい",        "group": "Economy"},
    {"name": "EfficientDailyMobility",   "label": "日常移動コストを抑えたい",        "group": "Economy"},
    # Lifestyle
    {"name": "DrivingEnjoyment",     "label": "運転そのものを楽しみたい",       "group": "Lifestyle"},
    {"name": "AdventureLifestyle",   "label": "冒険感を楽しみたい",             "group": "Lifestyle"},
    {"name": "OutdoorLifestyle",     "label": "アウトドア生活を楽しみたい",     "group": "Lifestyle"},
    {"name": "EmotionalAttachment",  "label": "愛着を持てる車に乗りたい",      "group": "Lifestyle"},
    {"name": "PersonalExpression",   "label": "自分らしさを表現したい",         "group": "Lifestyle"},
    {"name": "PremiumFeeling",       "label": "上質感を感じたい",               "group": "Lifestyle"},
    {"name": "ExcitingAcceleration", "label": "加速感を楽しみたい",             "group": "Lifestyle"},
    {"name": "StatusRecognition",    "label": "周囲から良く見られたい",         "group": "Lifestyle"},
    # Urban
    {"name": "UrbanManeuverability", "label": "狭い道でも扱いやすくしたい",        "group": "Urban"},
    {"name": "CompactParkingEase",   "label": "小さい駐車場でも停めやすくしたい", "group": "Urban"},
    {"name": "ShortTripEfficiency",  "label": "短距離移動を効率化したい",          "group": "Urban"},
    {"name": "QuickErrandMobility",  "label": "ちょっとした移動を楽にしたい",     "group": "Urban"},
    # Accessibility
    {"name": "EasyEntryExit",     "label": "乗り降りを楽にしたい",       "group": "Accessibility"},
    {"name": "LowPhysicalBurden", "label": "身体負担を減らしたい",       "group": "Accessibility"},
    {"name": "AccessibleSeating", "label": "座りやすい姿勢を確保したい", "group": "Accessibility"},
    {"name": "CaregiverSupport",  "label": "介護・送迎を楽にしたい",     "group": "Accessibility"},
    # EV
    {"name": "EnvironmentalResponsibility", "label": "環境配慮したい",            "group": "EV"},
    {"name": "ChargingConfidence",          "label": "充電不安を減らしたい",      "group": "EV"},
    {"name": "QuietElectricExperience",     "label": "EVの静かさを楽しみたい",    "group": "EV"},
    {"name": "EnergyEfficiency",            "label": "エネルギー効率を高めたい",  "group": "EV"},
]

# EC キーワード → 新 Need マッピング（優先度順）
EC_TO_NEW_NEEDS: list[tuple[str, list[str]]] = [
    ("ChildSafety",            ["子供の安全", "チャイルドシート", "後席安全", "キッズ安全", "子供を安全"]),
    ("EasyChildPickup",        ["乗せ降ろし", "子供の乗降", "チャイルドシート装着", "スライドドア"]),
    ("FamilyConversation",     ["家族で会話", "ファミリー空間", "会話しやすい"]),
    ("LargeCargoForFamily",    ["ベビーカー", "乳母車", "ベビー用品", "家族の荷物"]),
    ("WeekendFamilyTrip",      ["家族旅行", "ドライブ旅行", "週末旅行"]),
    ("ChildMonitoringEase",    ["後席確認", "子供の様子", "ルームミラー", "後席モニタ"]),
    ("StressFreeSchoolPickup", ["送迎", "学校", "幼稚園", "塾", "習い事の送迎"]),
    ("PetFriendlyTravel",      ["ペット", "愛犬", "犬", "猫", "動物"]),
    ("FamilyComfort",          ["家族全員", "ファミリー快適", "みんなが快適"]),
    ("EasyParking",            ["駐車", "バックカメラ", "パーキングセンサー", "駐車支援", "縦列駐車", "立体駐車"]),
    ("VisibilityConfidence",   ["視界", "見やすい", "周囲確認", "バックモニター", "全周囲"]),
    ("AccidentAnxietyReduction",["事故不安", "衝突", "Honda SENSING", "緊急ブレーキ", "追突防止"]),
    ("NightDrivingConfidence", ["夜間", "夜道", "暗い道", "LEDライト", "ハイビーム"]),
    ("SnowDrivingConfidence",  ["雪道", "雪", "凍結", "4WD", "AWD", "スリップ", "冬道"]),
    ("BeginnerFriendlyDriving",["初心者", "ペーパードライバー", "扱いやすい", "運転しやすい"]),
    ("ElderlyDrivingSupport",  ["高齢", "シニア", "年配", "高齢者の運転", "親の運転"]),
    ("DrivingConfidence",      ["運転不安", "安心して運転", "運転が苦手", "自信がない"]),
    ("FatigueReduction",       ["疲れない", "疲労軽減", "長距離疲労", "腰への負担"]),
    ("QuietCabinExperience",   ["静か", "静粛性", "騒音", "防音", "NVH", "ロードノイズ"]),
    ("SmoothRideComfort",      ["乗り心地", "柔らかい乗り", "段差", "サスペンション", "振動が少ない"]),
    ("StressFreeCommute",      ["通勤", "毎日の移動", "渋滞ストレス", "通勤渋滞"]),
    ("RelaxingDrive",          ["リラックス", "気持ちよく走る", "ゆったり", "余裕ある運転"]),
    ("ComfortableLongDistanceTravel",["長距離", "高速道路", "遠出", "ロングドライブ"]),
    ("ClimateComfort",         ["エアコン", "車内温度", "シートヒーター", "暖かい", "涼しい"]),
    ("FlexibleCargoSpace",     ["荷物が多い", "積載量", "荷室容量", "収納力"]),
    ("OutdoorGearTransport",   ["アウトドア用品", "キャンプ道具", "サーフボード", "スキー板", "自転車"]),
    ("EasyLoading",            ["積み下ろし", "テールゲート", "開口部が広い", "積みやすい"]),
    ("LargeShoppingCapacity",  ["まとめ買い", "スーパーの荷物", "買い物が多い"]),
    ("SportsEquipmentTransport",["ゴルフ用品", "野球道具", "サッカー", "スポーツバッグ"]),
    ("FlatSeatUtility",        ["車中泊", "フルフラット", "シートアレンジ", "マジックシート"]),
    ("LowFuelAnxiety",         ["燃料代", "ガソリン代", "燃費不安", "給油頻度"]),
    ("MaintenanceCostReduction",["維持費", "メンテナンス費用", "修理費", "保険料"]),
    ("LongTermReliability",    ["長く乗る", "耐久性", "信頼性", "壊れない"]),
    ("ResaleValueRetention",   ["リセール", "下取り価格", "売却価値"]),
    ("EfficientDailyMobility", ["コスパ", "経済的", "お得", "日常移動コスト"]),
    ("DrivingEnjoyment",       ["運転を楽しむ", "走り", "スポーティな走り", "エンジン音"]),
    ("AdventureLifestyle",     ["冒険", "非日常", "探検"]),
    ("OutdoorLifestyle",       ["アウトドア", "キャンプ", "自然", "オフロード", "山道"]),
    ("EmotionalAttachment",    ["愛着", "一目惚れ", "ずっと乗りたい", "憧れ"]),
    ("PersonalExpression",     ["個性", "自分らしさ", "こだわり", "オリジナル"]),
    ("PremiumFeeling",         ["上質", "高級感", "プレミアム", "洗練"]),
    ("ExcitingAcceleration",   ["加速", "ターボ", "パワー", "スポーツ走行"]),
    ("StatusRecognition",      ["かっこいい", "ステータス", "周囲の反応", "目立つ"]),
    ("UrbanManeuverability",   ["狭い道", "取り回し", "小回り", "裏道"]),
    ("CompactParkingEase",     ["立体駐車場", "コンパクトカー", "全長が短い", "全幅が小さい"]),
    ("ShortTripEfficiency",    ["近距離", "ちょっとした移動", "日常の足"]),
    ("QuickErrandMobility",    ["お使い", "ちょっと出かける"]),
    ("EasyEntryExit",          ["乗り降り", "乗降しやすい", "足腰", "ステップが低い"]),
    ("LowPhysicalBurden",      ["身体負担", "腰への負担", "楽に乗れる"]),
    ("AccessibleSeating",      ["座りやすい", "着座位置", "シート高さ"]),
    ("CaregiverSupport",       ["介護", "車椅子", "お年寄り", "福祉"]),
    ("EnvironmentalResponsibility",["環境配慮", "エコ", "CO2削減", "地球環境"]),
    ("ChargingConfidence",     ["充電", "航続距離", "充電スポット", "急速充電"]),
    ("QuietElectricExperience",["EVの静かさ", "電気自動車", "モーター駆動"]),
    ("EnergyEfficiency",       ["エネルギー効率", "回生ブレーキ", "電費"]),
]

# 旧 Need（抽象カテゴリ）→ 新 Need フォールバックマッピング
OLD_TO_NEW_NEEDS: dict[str, list[str]] = {
    "safety":          ["DrivingConfidence", "AccidentAnxietyReduction", "EasyParking", "VisibilityConfidence"],
    "family":          ["FamilyComfort", "ChildSafety", "WeekendFamilyTrip", "StressFreeSchoolPickup"],
    "comfort":         ["FatigueReduction", "SmoothRideComfort", "RelaxingDrive", "QuietCabinExperience"],
    "space":           ["FlexibleCargoSpace", "FlatSeatUtility", "EasyLoading"],
    "fuel_efficiency": ["LowFuelAnxiety", "EfficientDailyMobility", "EnergyEfficiency"],
    "economy":         ["LowFuelAnxiety", "MaintenanceCostReduction", "EfficientDailyMobility"],
    "performance":     ["DrivingEnjoyment", "ExcitingAcceleration"],
    "reliability":     ["LongTermReliability", "MaintenanceCostReduction"],
    "quality":         ["LongTermReliability", "PremiumFeeling"],
    "cost":            ["LowFuelAnxiety", "MaintenanceCostReduction", "EfficientDailyMobility"],
    "maintenance_cost":["MaintenanceCostReduction", "LongTermReliability"],
    "price":           ["EfficientDailyMobility", "LowFuelAnxiety"],
    "affordability":   ["EfficientDailyMobility", "LongTermReliability"],
    "brand_loyalty":   ["EmotionalAttachment", "LongTermReliability"],
    "design":          ["PersonalExpression", "EmotionalAttachment", "PremiumFeeling"],
    "technology":      ["DrivingConfidence", "AccidentAnxietyReduction", "EasyParking"],
    "offroad":         ["OutdoorLifestyle", "AdventureLifestyle", "SnowDrivingConfidence"],
    "leisure":         ["OutdoorLifestyle", "DrivingEnjoyment", "WeekendFamilyTrip"],
    "lifestyle_change":["PersonalExpression", "AdventureLifestyle", "EmotionalAttachment"],
    "nostalgia":       ["EmotionalAttachment"],
    "rarity":          ["PersonalExpression", "StatusRecognition"],
    "child_friendly":  ["ChildSafety", "EasyChildPickup", "FamilyComfort"],
}

def derive_consumer_needs(old_needs: list[str], ec_names: list[str]) -> set[str]:
    """旧Need一覧 + EC名リストから新生活欲求 Need の名前セットを導出する"""
    new_needs: set[str] = set()
    ec_text = " ".join(ec_names)
    for need_name, keywords in EC_TO_NEW_NEEDS:
        if any(kw in ec_text for kw in keywords):
            new_needs.add(need_name)
    for old_need in old_needs:
        for nn in OLD_TO_NEW_NEEDS.get(old_need, []):
            new_needs.add(nn)
    if not new_needs:
        new_needs.add("EfficientDailyMobility")
    return new_needs


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-PURCHASE-DRIVER] PurchaseDriver マスタ（label付き）
# ─────────────────────────────────────────────────────────────────────────────
PURCHASE_DRIVER_LABELS = {
    "安全性能":           "safety_performance",
    "燃費・維持費":       "fuel_economy",
    "広さ・実用性":       "practicality",
    "デザイン・スタイル": "design_style",
    "ブランド・信頼性":   "brand_trust",
    "乗り心地・快適性":   "ride_comfort",
    "価格・コスパ":       "price_value",
    "先進技術・装備":     "tech_equipment",
    "家族・他者の意見":   "social_influence",
    "試乗体験":           "test_drive_experience",
    "その他":             "other",
}

_PURCHASE_DRIVER_CATEGORIES: dict[str, list[str]] = {
    "安全性能":           ["安全", "セーフティ", "プリクラッシュ", "衝突", "AEB", "ブレーキ", "安心"],
    "デザイン・スタイル": ["デザイン", "スタイル", "外観", "カッコ", "見た目", "おしゃれ", "美し"],
    "価格・コスパ":       ["価格", "値段", "コスパ", "コスト", "安い", "経済的", "お得", "リーズナブル"],
    "家族・他者の意見":   ["家族", "妻", "夫", "子供", "友人", "知人", "勧め", "一緒", "相談"],
    "試乗体験":           ["試乗", "乗ってみ", "体感", "試してみ", "実際に乗", "試乗会"],
    "ブランド・信頼性":   ["ブランド", "信頼", "Honda", "品質", "実績", "評判"],
    "燃費・維持費":       ["燃費", "維持費", "ハイブリッド", "経済", "ランニング", "ガソリン代", "節約"],
    "乗り心地・快適性":   ["乗り心地", "快適", "静か", "静粛", "ゆったり", "疲れない"],
    "先進技術・装備":     ["技術", "装備", "システム", "先進", "ハイテク", "ナビ", "自動", "最新"],
    "広さ・実用性":       ["広", "実用", "収納", "荷物", "使いやす", "便利", "積める"],
}

def _categorize_purchase_driver(text: str) -> str:
    if not text:
        return "その他"
    for category, keywords in _PURCHASE_DRIVER_CATEGORIES.items():
        if any(kw in text for kw in keywords):
            return category
    return "その他"


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-REGRET] Regret マスタ
# ─────────────────────────────────────────────────────────────────────────────
REGRET_CATEGORY_LABELS = {
    "fuel_cost":      "燃費・燃料コスト",   "cargo_space":    "荷室・収納不足",
    "ride_quality":   "乗り心地・静粛性",   "size_too_large": "車体が大きすぎる",
    "size_too_small": "車体が小さすぎる",   "price":          "価格・コスト",
    "maintenance":    "維持費・メンテナンス","design":         "デザイン",
    "technology":     "技術・装備不足",     "other":          "その他",
}


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-CAPABILITY] Capability マスタ（v3新規）
# Feature.category → Capability のマッピング
# ─────────────────────────────────────────────────────────────────────────────
CAPABILITY_MASTER = [
    {"name": "SafetyPerformance",  "label": "安全性能",
     "description": "衝突回避・被害軽減・乗員保護に関わる総合安全能力",  "category": "safety"},
    {"name": "FuelEfficiency",     "label": "燃費・エネルギー効率",
     "description": "燃料消費の低減・電動化によるエネルギー最適化能力", "category": "fuel_efficiency"},
    {"name": "DesignAppeal",       "label": "デザイン魅力",
     "description": "外観・内装の美しさ・個性・ブランドイメージの訴求力","category": "design"},
    {"name": "TechInnovation",     "label": "先進技術",
     "description": "コネクテッド・自動化・デジタル化による利便性向上",  "category": "technology"},
    {"name": "SpaceUtility",       "label": "空間・収納",
     "description": "室内空間の広さ・荷物収納・シートアレンジの柔軟性", "category": "space"},
    {"name": "RideComfort",        "label": "快適・静粛性",
     "description": "乗り心地・静粛性・疲労軽減の快適さ",               "category": "comfort"},
    {"name": "FamilyFriendly",     "label": "ファミリー対応",
     "description": "子供・家族の乗降・チャイルドシート・後席快適性",   "category": "family"},
    {"name": "OffRoadCapability",  "label": "オフロード・走破性",
     "description": "悪路・雪道・山道などでの走行安定性・牽引能力",     "category": "offroad"},
    {"name": "GeneralPerformance", "label": "総合性能",
     "description": "走行性能・信頼性・コストパフォーマンスを含む総合的車両能力","category": "general"},
]

# Capability → Need マッピング（v3: 生活欲求型 55件）
CAPABILITY_TO_NEW_NEEDS = {
    "SafetyPerformance":  [
        "AccidentAnxietyReduction", "DrivingConfidence", "EasyParking",
        "VisibilityConfidence", "NightDrivingConfidence", "SnowDrivingConfidence",
        "BeginnerFriendlyDriving", "ElderlyDrivingSupport", "ChildSafety",
    ],
    "FuelEfficiency":     [
        "LowFuelAnxiety", "MaintenanceCostReduction", "EfficientDailyMobility",
        "EnvironmentalResponsibility", "EnergyEfficiency",
    ],
    "DesignAppeal":       [
        "PersonalExpression", "EmotionalAttachment", "PremiumFeeling", "StatusRecognition",
    ],
    "TechInnovation":     [
        "DrivingConfidence", "EasyParking", "AccidentAnxietyReduction",
        "StressFreeCommute", "ComfortableLongDistanceTravel",
    ],
    "SpaceUtility":       [
        "FlexibleCargoSpace", "FlatSeatUtility", "EasyLoading",
        "LargeCargoForFamily", "FamilyComfort", "LargeShoppingCapacity",
    ],
    "RideComfort":        [
        "SmoothRideComfort", "QuietCabinExperience", "FatigueReduction",
        "RelaxingDrive", "ComfortableLongDistanceTravel", "StressFreeCommute",
    ],
    "FamilyFriendly":     [
        "ChildSafety", "EasyChildPickup", "FamilyConversation", "FamilyComfort",
        "LargeCargoForFamily", "WeekendFamilyTrip", "StressFreeSchoolPickup",
        "PetFriendlyTravel", "ChildMonitoringEase",
    ],
    "OffRoadCapability":  [
        "OutdoorLifestyle", "AdventureLifestyle", "SnowDrivingConfidence",
        "OutdoorGearTransport", "SportsEquipmentTransport",
    ],
    "GeneralPerformance": [
        "DrivingEnjoyment", "ExcitingAcceleration", "LongTermReliability",
        "EfficientDailyMobility", "MaintenanceCostReduction",
    ],
}

# Capability → Regret（軽減する後悔）マッピング
CAPABILITY_TO_REGRETS = {
    "SafetyPerformance":  ["ride_quality", "maintenance"],
    "FuelEfficiency":     ["fuel_cost", "maintenance"],
    "DesignAppeal":       ["design"],
    "TechInnovation":     ["technology"],
    "SpaceUtility":       ["cargo_space", "size_too_small"],
    "RideComfort":        ["ride_quality"],
    "FamilyFriendly":     ["cargo_space", "size_too_small"],
    "OffRoadCapability":  [],
    "GeneralPerformance": ["ride_quality", "maintenance", "price"],
}

# Capability → DecisionStyle マッピング
CAPABILITY_TO_DECISION_STYLES = {
    "SafetyPerformance":  ["Authority-driven", "Satisficer", "Delegator"],
    "FuelEfficiency":     ["Maximizer", "Satisficer"],
    "DesignAppeal":       ["Intuitive", "Impulsive"],
    "TechInnovation":     ["Maximizer", "Authority-driven"],
    "SpaceUtility":       ["Maximizer", "Satisficer", "Delegator"],
    "RideComfort":        ["Intuitive", "Satisficer"],
    "FamilyFriendly":     ["Satisficer", "Delegator", "Maximizer"],
    "OffRoadCapability":  ["Intuitive", "Impulsive", "Maximizer"],
    "GeneralPerformance": ["Maximizer", "Satisficer", "Authority-driven"],
}


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-EC-LABEL] EvaluationCriteria → Capability label キーワードルール
# 優先度順に検査（最初にマッチしたカテゴリを採用）
# ─────────────────────────────────────────────────────────────────────────────
EC_LABEL_KEYWORDS = [
    ("SafetyPerformance", [
        "安全", "衝突", "ブレーキ", "エアバッグ", "SENSING", "センシング",
        "緊急", "自動ブレーキ", "警告", "車線逸脱", "ドライバーモニタ",
    ]),
    ("FuelEfficiency", [
        "燃費", "ハイブリッド", "e:HEV", "eHEV", "エコ", "電費",
        "充電", "ガソリン代", "低燃費", "省エネ", "CO2",
    ]),
    ("DesignAppeal", [
        "デザイン", "スタイル", "外観", "内装", "カラー", "色",
        "見た目", "おしゃれ", "かっこいい", "美し", "スタイリッシュ",
        "インテリア", "エクステリア",
    ]),
    ("TechInnovation", [
        "ナビ", "ACC", "自動運転", "コネクト", "カメラ", "センサー",
        "先進", "技術", "デジタル", "Honda CONNECT", "ETC",
        "音声", "スマホ", "ヘッドアップ", "モニター",
    ]),
    ("SpaceUtility", [
        "広さ", "室内", "収納", "荷室", "シートアレンジ", "積載",
        "ラゲッジ", "トランク", "フラット", "空間", "容量",
    ]),
    ("RideComfort", [
        "乗り心地", "静粛", "快適", "疲労", "NVH", "振動", "騒音",
        "サスペンション", "しなやか", "フラット感", "ゆったり",
    ]),
    ("FamilyFriendly", [
        "家族", "子供", "チャイルド", "送迎", "スライドドア",
        "ベビーカー", "育児", "ファミリー", "後席", "子育て",
    ]),
    ("OffRoadCapability", [
        "悪路", "オフロード", "4WD", "AWD", "走破", "雪道",
        "アウトドア", "牽引", "地上高",
    ]),
]
EC_LABEL_DEFAULT = "GeneralPerformance"

def classify_ec_label(name: str) -> str:
    """EvaluationCriteria.name から Capability ラベルを分類するルール"""
    for cap_name, keywords in EC_LABEL_KEYWORDS:
        if any(kw in name for kw in keywords):
            return cap_name
    return EC_LABEL_DEFAULT


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-VEHICLE-MODEL] VehicleModel マスタ（v3拡張プロパティ）
# body_type選択肢: Sedan/Hatchback/Wagon/SUV/CrossoverSUV/Minivan/CompactVan/
#                  Coupe/Convertible/Roadster/KeiCar/KeiVan/CommercialTruck/OffRoadVehicle
# segment選択肢:   A_Segment/B_Segment/C_Segment/D_Segment/E_Segment/F_Segment/
#                  Kei_Segment/CompactSUV/MidSizeSUV/CompactMinivan/LargeMinivan
# category選択肢:  Passenger/Commercial/Performance/Luxury/Electrified/Utility
# ─────────────────────────────────────────────────────────────────────────────
VEHICLE_MODEL_MASTER: dict[str, dict] = {
    "FIT":               {"segment": "B_Segment",      "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "フィット":           {"segment": "B_Segment",      "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "フィット RS":        {"segment": "B_Segment",      "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Performance"},
    "フィットシャトル":   {"segment": "B_Segment",      "body_type": "Wagon",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "フィット シャトル":  {"segment": "B_Segment",      "body_type": "Wagon",          "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "SHUTTLE":           {"segment": "B_Segment",      "body_type": "Wagon",          "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "ステップワゴン":     {"segment": "LargeMinivan",   "body_type": "Minivan",        "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "Honda Step WGN":    {"segment": "LargeMinivan",   "body_type": "Minivan",        "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "ステップワゴン RG1": {"segment": "LargeMinivan",   "body_type": "Minivan",        "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "RG1型ステップワゴン":{"segment": "LargeMinivan",   "body_type": "Minivan",        "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "オデッセイ":         {"segment": "LargeMinivan",   "body_type": "Minivan",        "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "Honda Odyssey":     {"segment": "LargeMinivan",   "body_type": "Minivan",        "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "Honda ODYSSEY HYBRID ABSOLUTE": {"segment": "LargeMinivan", "body_type": "Minivan", "fuel_type": "Hybrid", "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "ODYSSEY RA6":       {"segment": "LargeMinivan",   "body_type": "Minivan",        "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "エリシオン":         {"segment": "LargeMinivan",   "body_type": "Minivan",        "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 8, "category": "Passenger"},
    "フリード":           {"segment": "CompactMinivan", "body_type": "CompactVan",     "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 6, "category": "Passenger"},
    "フリード スパイク":  {"segment": "CompactMinivan", "body_type": "CompactVan",     "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Utility"},
    "FREEDSPIKE":        {"segment": "CompactMinivan", "body_type": "CompactVan",     "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Utility"},
    "モビリオ":           {"segment": "CompactMinivan", "body_type": "CompactVan",     "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 7, "category": "Passenger"},
    "ジェイド":           {"segment": "CompactMinivan", "body_type": "Wagon",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 6, "category": "Passenger"},
    "ストリーム":         {"segment": "CompactMinivan", "body_type": "CompactVan",     "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 7, "category": "Passenger"},
    "ホンダ ストリーム RSZ": {"segment": "CompactMinivan", "body_type": "CompactVan",  "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 7, "category": "Passenger"},
    "N-BOX":             {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "N BOX":             {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "NBOXPLUS":          {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Utility"},
    "NBOXSLASH":         {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "N-BOX SLASH":       {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "N-ONE":             {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "N-WGN":             {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "ライフ":             {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "ゼスト":             {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "THATS":             {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "ホンダ ザッツ":      {"segment": "Kei_Segment",   "body_type": "KeiCar",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Passenger"},
    "VAMOS":             {"segment": "Kei_Segment",   "body_type": "KeiVan",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Utility"},
    "N-VAN":             {"segment": "Kei_Segment",   "body_type": "KeiVan",         "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Commercial"},
    "エアウェイブ":        {"segment": "B_Segment",    "body_type": "Wagon",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "エディックス":        {"segment": "B_Segment",    "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 6, "category": "Passenger"},
    "CIVIC":             {"segment": "C_Segment",     "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "CIVIC TYPE R":      {"segment": "C_Segment",     "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Performance"},
    "シビックTYPE R":     {"segment": "C_Segment",     "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Performance"},
    "シビック セダン":    {"segment": "C_Segment",     "body_type": "Sedan",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "シビック ハッチバック":{"segment": "C_Segment",   "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "インテグラ":         {"segment": "C_Segment",     "body_type": "Sedan",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Performance"},
    "インテグラ スポーツリミテッド": {"segment": "C_Segment", "body_type": "Sedan", "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Performance"},
    "PRELUDE":           {"segment": "C_Segment",     "body_type": "Coupe",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 4, "category": "Performance"},
    "CR-X":              {"segment": "B_Segment",     "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 2, "category": "Performance"},
    "ACCORD":            {"segment": "D_Segment",     "body_type": "Sedan",          "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "アコード":           {"segment": "D_Segment",     "body_type": "Sedan",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "アコード ハイブリッド EX": {"segment": "D_Segment", "body_type": "Sedan",        "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 5, "category": "Electrified"},
    "Honda アコードワゴン（2002年式）": {"segment": "D_Segment", "body_type": "Wagon","fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "Honda Accord Wagon":{"segment": "D_Segment",     "body_type": "Wagon",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "INSPIRE":           {"segment": "D_Segment",     "body_type": "Sedan",          "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "インサイト":         {"segment": "C_Segment",     "body_type": "Sedan",          "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 5, "category": "Electrified"},
    "GRACE":             {"segment": "B_Segment",     "body_type": "Sedan",          "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "VEZEL":             {"segment": "CompactSUV",    "body_type": "CrossoverSUV",   "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "ヴェゼル":           {"segment": "CompactSUV",    "body_type": "CrossoverSUV",   "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "CR-V":              {"segment": "MidSizeSUV",    "body_type": "SUV",            "fuel_type": "Gasoline", "drive_type": "4WD", "seating_capacity": 5, "category": "Passenger"},
    "HR-V":              {"segment": "CompactSUV",    "body_type": "SUV",            "fuel_type": "Gasoline", "drive_type": "4WD", "seating_capacity": 5, "category": "Passenger"},
    "クロスロード":        {"segment": "CompactSUV",   "body_type": "OffRoadVehicle", "fuel_type": "Gasoline", "drive_type": "4WD", "seating_capacity": 5, "category": "Utility"},
    "S660":              {"segment": "Kei_Segment",   "body_type": "Convertible",    "fuel_type": "Gasoline", "drive_type": "MR",  "seating_capacity": 2, "category": "Performance"},
    "Honda S660":        {"segment": "Kei_Segment",   "body_type": "Convertible",    "fuel_type": "Gasoline", "drive_type": "MR",  "seating_capacity": 2, "category": "Performance"},
    "S2000":             {"segment": "D_Segment",     "body_type": "Roadster",       "fuel_type": "Gasoline", "drive_type": "FR",  "seating_capacity": 2, "category": "Performance"},
    "S2000 TypeS":       {"segment": "D_Segment",     "body_type": "Roadster",       "fuel_type": "Gasoline", "drive_type": "FR",  "seating_capacity": 2, "category": "Performance"},
    "CR-Z":              {"segment": "C_Segment",     "body_type": "Coupe",          "fuel_type": "Hybrid",   "drive_type": "FWD", "seating_capacity": 4, "category": "Performance"},
    "NSX":               {"segment": "E_Segment",     "body_type": "Coupe",          "fuel_type": "Hybrid",   "drive_type": "AWD", "seating_capacity": 2, "category": "Performance"},
    "LEGEND":            {"segment": "E_Segment",     "body_type": "Sedan",          "fuel_type": "Hybrid",   "drive_type": "AWD", "seating_capacity": 5, "category": "Luxury"},
    "ACTY TRUCK":        {"segment": "Kei_Segment",   "body_type": "CommercialTruck","fuel_type": "Gasoline", "drive_type": "FR",  "seating_capacity": 2, "category": "Commercial"},
    "Honda e":           {"segment": "B_Segment",     "body_type": "Hatchback",      "fuel_type": "Electric", "drive_type": "RWD", "seating_capacity": 4, "category": "Electrified"},
    "ホンダ・フィット（GD1後期）": {"segment": "B_Segment", "body_type": "Hatchback","fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
    "2008年型 FIT（FF）": {"segment": "B_Segment",    "body_type": "Hatchback",      "fuel_type": "Gasoline", "drive_type": "FWD", "seating_capacity": 5, "category": "Passenger"},
}


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-VEHICLE-ROLE] VehicleOwnership.vehicle_role 導出ルール
# usage_pattern キーワード → vehicle_role（複数設定可）
# ─────────────────────────────────────────────────────────────────────────────
USAGE_TO_ROLE: list[tuple[str, str]] = [
    ("family",    "FamilyVehicle"),
    ("childcare", "ChildcareVehicle"),
    ("elderly",   "ElderlySupportVehicle"),
    ("commute",   "CommuteVehicle"),
    ("business",  "BusinessVehicle"),
    ("outdoor",   "OutdoorVehicle"),
    ("camping",   "OutdoorVehicle"),
    ("leisure",   "HobbyVehicle"),
    ("sport",     "HobbyVehicle"),
    ("shopping",  "CityVehicle"),
]

def derive_vehicle_role(usage_pattern: str | None, is_current: bool) -> list[str]:
    """usage_pattern から vehicle_role リストを導出する"""
    up = (usage_pattern or "").lower()
    roles = [role for kw, role in USAGE_TO_ROLE if kw in up]
    # 重複排除（順序保持）
    seen: set[str] = set()
    roles = [r for r in roles if not (r in seen or seen.add(r))]
    if not roles:
        roles = ["PrimaryVehicle"] if is_current else ["SecondaryVehicle"]
    return roles


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-VEHICLE-COUNT] Consumer.household_vehicle_count 抽出ルール
# ─────────────────────────────────────────────────────────────────────────────
_VEHICLE_COUNT_PATTERNS = [
    re.compile(r'(\d)\s*台\s*(所有|持ち|保有)'),
    re.compile(r'(計|合計)\s*(\d)\s*台'),
    re.compile(r'世帯\s*(\d)\s*台'),
    re.compile(r'家\s*に\s*(\d)\s*台'),
    re.compile(r'一家に(\d)\s*台'),
]

def extract_vehicle_count(story_text) -> int | None:
    """ストーリーテキストから世帯保有台数をルールで抽出する"""
    text = str(story_text)
    for pattern in _VEHICLE_COUNT_PATTERNS:
        m = pattern.search(text)
        if m:
            for g in m.groups():
                if g and g.isdigit():
                    return int(g)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-FEATURE-CATEGORY] TechnicalFeature カテゴリ推論
# ─────────────────────────────────────────────────────────────────────────────
_FEATURE_CATEGORY_MAP: dict[str, list[str]] = {
    "safety":          ["安全", "セーフティ", "Safety", "衝突", "プリクラッシュ", "ブレーキ", "レーン", "モニター"],
    "fuel_efficiency": ["燃費", "ハイブリッド", "HEV", "PHEV", "EV", "充電", "回生", "エコ"],
    "comfort":         ["快適", "乗り心地", "静粛", "シート", "マッサージ", "サスペンション", "防音"],
    "space":           ["広", "ラゲッジ", "収納", "室内", "3列", "荷室"],
    "design":          ["デザイン", "スタイル", "LED", "インテリア", "外観", "シルエット", "カラー"],
    "technology":      ["ナビ", "ディスプレイ", "HUD", "デジタル", "コネクト", "OTA", "自動", "AI"],
    "family":          ["ファミリー", "チャイルド", "スライド", "後席", "キャプテン"],
    "offroad":         ["4WD", "AWD", "オフロード", "悪路", "四駆", "KDSS"],
}

def _infer_feature_category(feat_text: str) -> str:
    for cat, kws in _FEATURE_CATEGORY_MAP.items():
        if any(kw in feat_text for kw in kws):
            return cat
    return "general"


# ─────────────────────────────────────────────────────────────────────────────
# [RULE-OUTCOME-LABEL] Outcome.label 導出（satisfaction_score 基準）
# ─────────────────────────────────────────────────────────────────────────────
def derive_outcome_label(score) -> str:
    if score is None:
        return "Unknown"
    score = int(score)
    if score >= 4:
        return "Satisfied"
    elif score == 3:
        return "Neutral"
    else:
        return "Dissatisfied"


# =============================================================================
# ── GraphBuilder クラス ───────────────────────────────────────────────────────
# =============================================================================

class GraphBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def clear_graph(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("Graph cleared.")

    def create_constraints(self):
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Consumer)           REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ds:DecisionStyle)     REQUIRE ds.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (le:LifeEvent)         REQUIRE le.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Trigger)            REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Need)               REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:EvaluationCriteria) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:PurchaseDriver)     REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:VehicleModel)       REQUIRE v.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (tf:TechnicalFeature)  REQUIRE tf.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (cap:Capability)       REQUIRE cap.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Outcome)            REQUIRE o.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Regret)             REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (vo:VehicleOwnership)  REQUIRE vo.id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for c in constraints:
                session.run(c)
        print("Constraints created.")

    def init_master_nodes(self):
        """Capability/Need/Regret などマスタノードを初期化する（graph全体で1回だけ実行）"""
        with self.driver.session() as session:
            # Need ノード（55件 生活欲求型）
            for need in NEW_NEED_MASTER:
                session.run("""
                    MERGE (n:Need {name: $name})
                    SET n.label = $label,
                        n.group = $group
                """, name=need["name"], label=need["label"], group=need["group"])

            # Capability ノード
            for cap in CAPABILITY_MASTER:
                session.run("""
                    MERGE (c:Capability {name: $name})
                    SET c.label       = $label,
                        c.description = $description,
                        c.category    = $category
                """, **cap)

            # Capability → Need（新生活欲求型）
            for cap_name, need_names in CAPABILITY_TO_NEW_NEEDS.items():
                for need_name in need_names:
                    session.run("""
                        MATCH (cap:Capability {name: $cap_name})
                        MATCH (n:Need {name: $need_name})
                        MERGE (cap)-[:SUPPORTS]->(n)
                    """, cap_name=cap_name, need_name=need_name)

            # Capability → Regret
            for cap_name, regret_names in CAPABILITY_TO_REGRETS.items():
                for regret_name in regret_names:
                    session.run("""
                        MATCH (cap:Capability {name: $cap_name})
                        MATCH (r:Regret {name: $regret_name})
                        MERGE (cap)-[:REDUCES]->(r)
                    """, cap_name=cap_name, regret_name=regret_name)

            # Capability → DecisionStyle
            for cap_name, style_names in CAPABILITY_TO_DECISION_STYLES.items():
                for style_name in style_names:
                    session.run("""
                        MATCH (cap:Capability {name: $cap_name})
                        MATCH (d:DecisionStyle {name: $style_name})
                        MERGE (cap)-[:APPEALS_TO]->(d)
                    """, cap_name=cap_name, style_name=style_name)

        print("Master nodes (Capability) initialized.")

    def load_consumer_decisions(self):
        decisions = json.loads(CONSUMER_DECISIONS_PATH.read_text(encoding="utf-8"))

        stories_map: dict[str, dict] = {}
        if CONSUMER_STORIES_PATH.exists():
            for s in json.loads(CONSUMER_STORIES_PATH.read_text(encoding="utf-8")):
                stories_map[s.get("story_id", s.get("id", ""))] = s

        print(f"Loading {len(decisions)} consumer decisions...")

        with self.driver.session() as session:
            for d in decisions:
                story_id = d.get("story_id", "unknown")
                ctx      = d.get("consumer_context", {})
                story    = stories_map.get(story_id, {})
                st_text  = story.get("story_text", {})

                # ── Consumer ──────────────────────────────────────────────
                raw_gender   = story.get("gender", "") or d.get("gender", "") or ""
                clean_gender = _clean_gender(raw_gender)
                country      = story.get("country", "") or d.get("country", "") or "日本"
                children_ages  = [str(a) for a in (ctx.get("children_ages") or []) if a]
                marital_status = ctx.get("marital_status") or "unknown"
                household_type = ctx.get("household_type") or "unknown"
                has_elderly    = ctx.get("has_elderly")

                # household_vehicle_count: ルールベース抽出
                hvc = extract_vehicle_count(story.get("story_text", ""))

                session.run("""
                    MERGE (c:Consumer {id: $id})
                    SET c.family_size              = $family_size,
                        c.children                 = $children,
                        c.children_ages            = $children_ages,
                        c.marital_status           = $marital_status,
                        c.household_type           = $household_type,
                        c.has_elderly              = $has_elderly,
                        c.household_vehicle_count  = $household_vehicle_count,
                        c.title                    = $title,
                        c.gender                   = $gender,
                        c.age_group                = $age_group,
                        c.location                 = $location,
                        c.country                  = $country,
                        c.occupation               = $occupation,
                        c.income_range             = $income_range,
                        c.driving_frequency        = $driving_frequency,
                        c.mobility_pattern         = $mobility_pattern,
                        c.values                   = $values,
                        c.physical_notes           = $physical_notes
                """,
                    id                    = story_id,
                    family_size           = ctx.get("family_size"),
                    children              = ctx.get("children", 0),
                    children_ages         = children_ages,
                    marital_status        = marital_status,
                    household_type        = household_type,
                    has_elderly           = has_elderly,
                    household_vehicle_count = hvc,
                    title                 = d.get("title", story.get("title", "")),
                    gender                = clean_gender,
                    age_group             = story.get("age_group", "") or d.get("age_group", "") or "",
                    location              = story.get("location", "") or d.get("location", "") or "",
                    country               = country,
                    occupation            = story.get("occupation", ""),
                    income_range          = story.get("income_range", ""),
                    driving_frequency     = story.get("driving_frequency", ""),
                    mobility_pattern      = story.get("mobility_pattern", ""),
                    values                = story.get("values", ""),
                    physical_notes        = story.get("physical_notes", ""),
                )

                # ── DecisionStyle ──────────────────────────────────────────
                ds_name = d.get("decision_style", "").strip()
                if ds_name and ds_name in DECISION_STYLE_MASTER:
                    dm = DECISION_STYLE_MASTER[ds_name]
                    session.run("""
                        MERGE (ds:DecisionStyle {name: $name})
                        SET ds.label                = $label,
                            ds.description          = $description,
                            ds.decision_behavior     = $decision_behavior,
                            ds.information_preference= $information_preference
                        WITH ds
                        MATCH (c:Consumer {id: $cid})
                        MERGE (c)-[:HAS_DECISION_STYLE]->(ds)
                    """,
                        name                 = ds_name,
                        label                = dm["label"],
                        description          = dm["description"],
                        decision_behavior    = dm["decision_behavior"],
                        information_preference = dm["information_preference"],
                        cid                  = story_id,
                    )

                # ── LifeEvent ──────────────────────────────────────────────
                _le = d.get("life_event")
                if isinstance(_le, list):
                    _le = _le[0] if _le else None
                life_event_val = _le
                if isinstance(life_event_val, str) and life_event_val:
                    le_key = life_event_val if life_event_val in LIFE_EVENT_LABELS \
                             else _kikkake_to_life_event(story.get("kikkake", "") or life_event_val)
                else:
                    le_key = _kikkake_to_life_event(story.get("kikkake", ""))

                if le_key:
                    session.run("""
                        MERGE (le:LifeEvent {name: $name})
                        SET le.label = $label
                        WITH le
                        MATCH (c:Consumer {id: $cid})
                        MERGE (c)-[:EXPERIENCED]->(le)
                    """, name=le_key, label=LIFE_EVENT_LABELS.get(le_key, le_key), cid=story_id)

                # ── Trigger ────────────────────────────────────────────────
                _tv = d.get("trigger", "")
                if isinstance(_tv, list):
                    _tv = _tv[0] if _tv else ""
                trigger_val = str(_tv).strip()
                if trigger_val and trigger_val in TRIGGER_LABELS:
                    trigger_key = trigger_val
                elif trigger_val:
                    trigger_key = _kikkake_to_trigger(trigger_val)
                else:
                    kk = story.get("kikkake", "")
                    trigger_key = _kikkake_to_trigger(kk) if kk else None

                if trigger_key:
                    session.run("""
                        MERGE (t:Trigger {name: $name})
                        SET t.label = $label
                        WITH t
                        MATCH (c:Consumer {id: $cid})
                        MERGE (c)-[:HAS_TRIGGER]->(t)
                    """, name=trigger_key, label=TRIGGER_LABELS.get(trigger_key, trigger_key), cid=story_id)

                # ── Needs（生活欲求型 v3）──────────────────────────────────
                old_needs = [n.strip() for n in d.get("needs", []) if n.strip()]
                ec_names  = [c.strip() for c in d.get("evaluation_criteria", []) if c.strip()]
                new_needs = derive_consumer_needs(old_needs, ec_names)
                for need_name in new_needs:
                    session.run("""
                        MATCH (n:Need {name: $name})
                        MATCH (c:Consumer {id: $cid})
                        MERGE (c)-[:HAS_NEED]->(n)
                    """, name=need_name, cid=story_id)

                # ── EvaluationCriteria ─────────────────────────────────────
                for crit in d.get("evaluation_criteria", []):
                    crit = crit.strip()
                    if crit:
                        ec_label = classify_ec_label(crit)
                        session.run("""
                            MERGE (e:EvaluationCriteria {name: $name})
                            SET e.label = $label
                            WITH e
                            MATCH (c:Consumer {id: $cid})
                            MERGE (c)-[:VALUED]->(e)
                        """, name=crit[:200], label=ec_label, cid=story_id)

                # ── PurchaseDriver ─────────────────────────────────────────
                pd_raw = d.get("purchase_driver", "")
                if not pd_raw and isinstance(st_text, dict):
                    pd_raw = st_text.get("deciding_factor", "")
                if not pd_raw:
                    pd_raw = story.get("most_satisfied", "")
                if pd_raw:
                    pd_category = _categorize_purchase_driver(pd_raw)
                    pd_label    = PURCHASE_DRIVER_LABELS.get(pd_category, "other")
                    session.run("""
                        MERGE (pd:PurchaseDriver {name: $category})
                        SET pd.label    = $label,
                            pd.raw_text = $raw_text
                        WITH pd
                        MATCH (c:Consumer {id: $cid})
                        MERGE (c)-[:DECIDED]->(pd)
                    """, category=pd_category, label=pd_label,
                        raw_text=pd_raw[:200], cid=story_id)

                # ── Considered vehicles ────────────────────────────────────
                purchased = (story.get("vehicle_model") or "").strip() or d.get("selected_vehicle", "").strip()
                all_opts  = list(story.get("considered_options") or d.get("considered_options") or [])
                for option in all_opts:
                    option = option.strip()
                    if option and option != purchased:
                        vm_props = VEHICLE_MODEL_MASTER.get(option, {})
                        session.run("""
                            MERGE (v:VehicleModel {name: $name})
                            SET v.segment          = coalesce($segment, v.segment),
                                v.body_type         = coalesce($body_type, v.body_type),
                                v.fuel_type         = coalesce($fuel_type, v.fuel_type),
                                v.drive_type        = coalesce($drive_type, v.drive_type),
                                v.seating_capacity  = coalesce($seating_capacity, v.seating_capacity),
                                v.category          = coalesce($category, v.category)
                            WITH v
                            MATCH (c:Consumer {id: $cid})
                            MERGE (c)-[:CONSIDERED]->(v)
                        """, name=option[:100], cid=story_id,
                            segment=vm_props.get("segment"),
                            body_type=vm_props.get("body_type"),
                            fuel_type=vm_props.get("fuel_type"),
                            drive_type=vm_props.get("drive_type"),
                            seating_capacity=vm_props.get("seating_capacity"),
                            category=vm_props.get("category"))

                # ── VehicleOwnership（現在の購入車）─────────────────────────
                satisfaction  = story.get("satisfaction_score") or d.get("satisfaction_score")
                purchase_year = d.get("purchase_year")
                if not purchase_year:
                    post_date = story.get("post_date", "") or d.get("post_date", "")
                    if post_date and len(str(post_date)) >= 4:
                        try:
                            purchase_year = int(str(post_date)[:4])
                        except (ValueError, TypeError):
                            pass

                vd          = d.get("vehicle_details") or {}
                vd_brand    = (vd.get("brand") or "Honda")[:50]
                vd_grade    = (vd.get("grade") or "")[:100] or None
                vd_my       = vd.get("model_year")
                vd_body     = (vd.get("body_color") or "")[:100] or None
                vd_interior = (vd.get("interior_color") or "")[:100] or None
                vd_opts     = [str(o)[:100] for o in (vd.get("optional_equipment") or []) if o]
                usage_pat   = ctx.get("usage", "")

                if purchased:
                    vm_props      = VEHICLE_MODEL_MASTER.get(purchased, {})
                    ownership_id  = f"{story_id}_current"
                    vehicle_roles = derive_vehicle_role(usage_pat, is_current=True)

                    # VehicleModel 作成・更新
                    session.run("""
                        MERGE (v:VehicleModel {name: $name})
                        SET v.brand            = $brand,
                            v.segment          = coalesce($segment, v.segment),
                            v.body_type         = coalesce($body_type, v.body_type),
                            v.fuel_type         = coalesce($fuel_type, v.fuel_type),
                            v.drive_type        = coalesce($drive_type, v.drive_type),
                            v.seating_capacity  = coalesce($seating_capacity, v.seating_capacity),
                            v.category          = coalesce($category, v.category)
                    """, name=purchased[:100], brand=vd_brand,
                        segment=vm_props.get("segment"),
                        body_type=vm_props.get("body_type"),
                        fuel_type=vm_props.get("fuel_type"),
                        drive_type=vm_props.get("drive_type"),
                        seating_capacity=vm_props.get("seating_capacity"),
                        category=vm_props.get("category"))

                    # VehicleOwnership ノード（is_current=true）
                    session.run("""
                        MERGE (vo:VehicleOwnership {id: $oid})
                        SET vo.purchase_year      = $purchase_year,
                            vo.model_year         = $model_year,
                            vo.satisfaction_score = $score,
                            vo.usage_pattern      = $usage,
                            vo.annual_mileage     = $mileage,
                            vo.is_current         = true,
                            vo.grade              = $grade,
                            vo.body_color         = $body_color,
                            vo.interior_color     = $interior_color,
                            vo.optional_equipment = $optional_equipment,
                            vo.vehicle_role       = $vehicle_role
                        WITH vo
                        MATCH (v:VehicleModel {name: $vname})
                        MERGE (vo)-[:OF_MODEL]->(v)
                        WITH vo
                        MATCH (c:Consumer {id: $cid})
                        MERGE (c)-[own:OWNED]->(vo)
                        SET own.decision_weight = 1.0
                    """,
                        oid               = ownership_id,
                        purchase_year     = purchase_year,
                        model_year        = int(vd_my) if vd_my else None,
                        score             = int(satisfaction) if satisfaction else None,
                        usage             = usage_pat,
                        mileage           = ctx.get("annual_mileage", "unknown"),
                        grade             = vd_grade,
                        body_color        = vd_body,
                        interior_color    = vd_interior,
                        optional_equipment= vd_opts,
                        vehicle_role      = vehicle_roles,
                        vname             = purchased[:100],
                        cid               = story_id,
                    )

                    # Outcome → VehicleOwnership -[RESULTED_IN]-> Outcome
                    outcome_text = d.get("outcome", "").strip()
                    if outcome_text:
                        outcome_label = derive_outcome_label(satisfaction)
                        session.run("""
                            MERGE (o:Outcome {name: $name})
                            SET o.label = $label
                            WITH o
                            MATCH (vo:VehicleOwnership {id: $oid})
                            MERGE (vo)-[ri:RESULTED_IN]->(o)
                            SET ri.score       = $score,
                                ri.description = $description,
                                ri.timing      = 'post_purchase'
                        """, name=outcome_text[:200], label=outcome_label,
                            oid=ownership_id,
                            score=int(satisfaction) if satisfaction else None,
                            description=outcome_text[:200])

                    # Regret → VehicleOwnership -[CAUSED_REGRET]-> Regret
                    for reg in d.get("regret", []):
                        if not isinstance(reg, dict):
                            continue
                        cat  = reg.get("category", "other")
                        desc = reg.get("description", "").strip()
                        sev  = reg.get("severity", 1)
                        if not cat:
                            continue
                        session.run("""
                            MERGE (r:Regret {name: $name})
                            SET r.label = $label
                            WITH r
                            MATCH (vo:VehicleOwnership {id: $oid})
                            MERGE (vo)-[cr:CAUSED_REGRET]->(r)
                            SET cr.description = $desc,
                                cr.severity    = $sev,
                                cr.timing      = 'post_purchase'
                        """,
                            name  = cat,
                            label = REGRET_CATEGORY_LABELS.get(cat, cat),
                            oid   = ownership_id,
                            desc  = desc[:200],
                            sev   = int(sev) if sev else 1,
                        )

                # ── 前所有車 ────────────────────────────────────────────────
                prev_vehicle = d.get("previous_vehicle")
                if prev_vehicle and isinstance(prev_vehicle, str) and prev_vehicle.strip():
                    prev_vehicle = prev_vehicle.strip()
                    prev_oid     = f"{story_id}_prev"
                    prev_roles   = derive_vehicle_role(ctx.get("usage", ""), is_current=False)
                    session.run("""
                        MERGE (v:VehicleModel {name: $vname})
                        WITH v
                        MERGE (vo:VehicleOwnership {id: $oid})
                        SET vo.is_current       = false,
                            vo.replacement_reason= $reason,
                            vo.vehicle_role      = $vehicle_role
                        MERGE (vo)-[:OF_MODEL]->(v)
                        WITH vo
                        MATCH (c:Consumer {id: $cid})
                        MERGE (c)-[own:OWNED]->(vo)
                        SET own.decision_weight = 0.5
                    """,
                        vname        = prev_vehicle[:100],
                        oid          = prev_oid,
                        reason       = trigger_key or "other",
                        vehicle_role = prev_roles,
                        cid          = story_id,
                    )

        print("Consumer decisions loaded.")

    def load_product_features(self):
        features_list = json.loads(PRODUCT_FEATURES_PATH.read_text(encoding="utf-8"))
        print(f"Loading {len(features_list)} product features...")

        with self.driver.session() as session:
            for pf in features_list:
                model_name = pf.get("model_name", "").strip()
                if not model_name:
                    continue

                vm_props = VEHICLE_MODEL_MASTER.get(model_name, {})
                session.run("""
                    MERGE (v:VehicleModel {name: $name})
                    SET v.price_range       = $price_range,
                        v.segment           = coalesce($segment, v.segment),
                        v.body_type         = coalesce($body_type, v.body_type),
                        v.fuel_type         = coalesce($fuel_type, v.fuel_type),
                        v.drive_type        = coalesce($drive_type, v.drive_type),
                        v.seating_capacity  = coalesce($seating_capacity, v.seating_capacity),
                        v.category          = coalesce($category, v.category)
                """,
                    name           = model_name,
                    price_range    = pf.get("specs", {}).get("price_range", ""),
                    segment        = vm_props.get("segment"),
                    body_type      = vm_props.get("body_type"),
                    fuel_type      = vm_props.get("fuel_type"),
                    drive_type     = vm_props.get("drive_type"),
                    seating_capacity = vm_props.get("seating_capacity"),
                    category       = vm_props.get("category"),
                )

                all_features = (
                    pf.get("features", [])
                    + pf.get("safety_features", [])
                    + pf.get("technology", [])
                )
                for feat in all_features:
                    feat = feat.strip()
                    if not feat:
                        continue
                    feat_cat = _infer_feature_category(feat)
                    session.run("""
                        MERGE (tf:TechnicalFeature {name: $name})
                        SET tf.category = $category
                        WITH tf
                        MATCH (cap:Capability {category: $category})
                        MERGE (tf)-[:REALIZES]->(cap)
                        WITH tf
                        MATCH (v:VehicleModel {name: $vname})
                        MERGE (v)-[:HAS_FEATURE]->(tf)
                    """,
                        name     = feat[:200],
                        vname    = model_name,
                        category = feat_cat,
                    )

        self._build_capability_influences()
        print("Product features loaded.")

    def _build_capability_influences(self):
        """Capability -[INFLUENCES]-> EvaluationCriteria を構築する"""
        print("Building Capability <-> EvaluationCriteria bridges...")
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ec:EvaluationCriteria)
                MATCH (cap:Capability {name: ec.label})
                MERGE (cap)-[r:INFLUENCES]->(ec)
                RETURN count(r) AS cnt
            """)
            cnt = result.single()["cnt"]
            print(f"Built {cnt} Capability->EvaluationCriteria bridges.")

    def get_stats(self) -> dict:
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS count
                ORDER BY count DESC
            """)
            node_counts = {r["label"]: r["count"] for r in result}

            result2 = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS rel_type, count(r) AS count
                ORDER BY count DESC
            """)
            rel_counts = {r["rel_type"]: r["count"] for r in result2}

        return {"nodes": node_counts, "relationships": rel_counts}


def main():
    builder = GraphBuilder()
    try:
        print("Building knowledge graph (v3 ontology)...")
        builder.clear_graph()
        builder.create_constraints()
        builder.init_master_nodes()
        builder.load_consumer_decisions()
        builder.load_product_features()

        stats = builder.get_stats()
        print("\n=== Graph Statistics ===")
        print("Nodes:")
        for label, count in stats["nodes"].items():
            print(f"  {label}: {count}")
        print("Relationships:")
        for rel, count in stats["relationships"].items():
            print(f"  {rel}: {count}")
    finally:
        builder.close()


if __name__ == "__main__":
    main()
