"""
update_ontology_v3_step5_needs.py
----------------------------------
Needノードを抽象カテゴリから「生活欲求」型の具体的Needに置き換える。

処理内容:
  5-1. 新 Need ノード（55件）を作成
  5-2. Consumer -[HAS_NEED]-> NewNeed を導出（旧Need + EC キーワードマッチ）
  5-3. Capability -[SUPPORTS]-> NewNeed を再構築
  5-4. 旧 Consumer -[HAS_NEED]-> OldNeed（22件）を削除
  5-5. 旧 Need ノード（抽象カテゴリ）を削除
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from neo4j import GraphDatabase

NEO4J_URI      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "KMixerOrigin2026")

# =============================================================================
# 新 Need マスタ（生活欲求型、55件）
# =============================================================================
NEW_NEED_MASTER = [
    # ── ファミリー・子育て ──────────────────────────────────────────────────
    {"name": "ChildSafety",            "label": "子供を安全に乗せたい",            "group": "Family"},
    {"name": "EasyChildPickup",        "label": "子供の乗せ降ろしを楽にしたい",    "group": "Family"},
    {"name": "FamilyConversation",     "label": "家族で会話しやすい空間が欲しい",  "group": "Family"},
    {"name": "FamilyComfort",          "label": "家族全員が快適に移動したい",      "group": "Family"},
    {"name": "LargeCargoForFamily",    "label": "ベビーカーや荷物を楽に積みたい", "group": "Family"},
    {"name": "WeekendFamilyTrip",      "label": "家族旅行を楽しみたい",           "group": "Family"},
    {"name": "ChildMonitoringEase",    "label": "後席の子供の様子を確認したい",    "group": "Family"},
    {"name": "StressFreeSchoolPickup", "label": "送迎のストレスを減らしたい",      "group": "Family"},
    {"name": "PetFriendlyTravel",      "label": "ペットと快適に移動したい",        "group": "Family"},
    # ── 安全・安心 ────────────────────────────────────────────────────────
    {"name": "EasyParking",              "label": "駐車を楽にしたい",              "group": "Safety"},
    {"name": "VisibilityConfidence",     "label": "周囲を見やすくしたい",          "group": "Safety"},
    {"name": "DrivingConfidence",        "label": "運転への不安を減らしたい",      "group": "Safety"},
    {"name": "AccidentAnxietyReduction", "label": "事故不安を減らしたい",          "group": "Safety"},
    {"name": "NightDrivingConfidence",   "label": "夜間運転を安心したい",          "group": "Safety"},
    {"name": "SnowDrivingConfidence",    "label": "雪道でも安心したい",            "group": "Safety"},
    {"name": "BeginnerFriendlyDriving", "label": "運転初心者でも扱いやすくしたい", "group": "Safety"},
    {"name": "ElderlyDrivingSupport",    "label": "高齢でも安全に運転したい",      "group": "Safety"},
    # ── 快適・疲労軽減 ────────────────────────────────────────────────────
    {"name": "FatigueReduction",              "label": "長時間運転で疲れたくない",    "group": "Comfort"},
    {"name": "QuietCabinExperience",          "label": "静かな空間で移動したい",      "group": "Comfort"},
    {"name": "SmoothRideComfort",             "label": "乗り心地を良くしたい",        "group": "Comfort"},
    {"name": "StressFreeCommute",             "label": "通勤ストレスを減らしたい",    "group": "Comfort"},
    {"name": "RelaxingDrive",                 "label": "リラックスして運転したい",    "group": "Comfort"},
    {"name": "ComfortableLongDistanceTravel", "label": "長距離移動を快適にしたい",    "group": "Comfort"},
    {"name": "ClimateComfort",                "label": "車内温度を快適に保ちたい",    "group": "Comfort"},
    # ── 荷物・収納 ────────────────────────────────────────────────────────
    {"name": "FlexibleCargoSpace",       "label": "荷物量に柔軟対応したい",           "group": "Cargo"},
    {"name": "OutdoorGearTransport",     "label": "アウトドア用品を積みたい",         "group": "Cargo"},
    {"name": "EasyLoading",              "label": "荷物を積み下ろししやすくしたい",   "group": "Cargo"},
    {"name": "LargeShoppingCapacity",    "label": "まとめ買いに対応したい",           "group": "Cargo"},
    {"name": "SportsEquipmentTransport", "label": "スポーツ用品を運びたい",           "group": "Cargo"},
    {"name": "FlatSeatUtility",          "label": "車中泊や大きな荷物に対応したい",   "group": "Cargo"},
    # ── 経済・維持費 ──────────────────────────────────────────────────────
    {"name": "LowFuelAnxiety",           "label": "燃料代不安を減らしたい",          "group": "Economy"},
    {"name": "MaintenanceCostReduction", "label": "維持費を抑えたい",                "group": "Economy"},
    {"name": "LongTermReliability",      "label": "長く安心して乗りたい",            "group": "Economy"},
    {"name": "ResaleValueRetention",     "label": "リセール価値を維持したい",        "group": "Economy"},
    {"name": "EfficientDailyMobility",   "label": "日常移動コストを抑えたい",        "group": "Economy"},
    # ── 楽しさ・ライフスタイル ────────────────────────────────────────────
    {"name": "DrivingEnjoyment",     "label": "運転そのものを楽しみたい",       "group": "Lifestyle"},
    {"name": "AdventureLifestyle",   "label": "冒険感を楽しみたい",             "group": "Lifestyle"},
    {"name": "OutdoorLifestyle",     "label": "アウトドア生活を楽しみたい",     "group": "Lifestyle"},
    {"name": "EmotionalAttachment",  "label": "愛着を持てる車に乗りたい",      "group": "Lifestyle"},
    {"name": "PersonalExpression",   "label": "自分らしさを表現したい",         "group": "Lifestyle"},
    {"name": "PremiumFeeling",       "label": "上質感を感じたい",               "group": "Lifestyle"},
    {"name": "ExcitingAcceleration", "label": "加速感を楽しみたい",             "group": "Lifestyle"},
    {"name": "StatusRecognition",    "label": "周囲から良く見られたい",         "group": "Lifestyle"},
    # ── 都市・コンパクト ──────────────────────────────────────────────────
    {"name": "UrbanManeuverability", "label": "狭い道でも扱いやすくしたい",        "group": "Urban"},
    {"name": "CompactParkingEase",   "label": "小さい駐車場でも停めやすくしたい", "group": "Urban"},
    {"name": "ShortTripEfficiency",  "label": "短距離移動を効率化したい",          "group": "Urban"},
    {"name": "QuickErrandMobility",  "label": "ちょっとした移動を楽にしたい",     "group": "Urban"},
    # ── バリアフリー・高齢者 ──────────────────────────────────────────────
    {"name": "EasyEntryExit",     "label": "乗り降りを楽にしたい",       "group": "Accessibility"},
    {"name": "LowPhysicalBurden", "label": "身体負担を減らしたい",       "group": "Accessibility"},
    {"name": "AccessibleSeating", "label": "座りやすい姿勢を確保したい", "group": "Accessibility"},
    {"name": "CaregiverSupport",  "label": "介護・送迎を楽にしたい",     "group": "Accessibility"},
    # ── EV・環境 ─────────────────────────────────────────────────────────
    {"name": "EnvironmentalResponsibility", "label": "環境配慮したい",            "group": "EV"},
    {"name": "ChargingConfidence",          "label": "充電不安を減らしたい",      "group": "EV"},
    {"name": "QuietElectricExperience",     "label": "EVの静かさを楽しみたい",    "group": "EV"},
    {"name": "EnergyEfficiency",            "label": "エネルギー効率を高めたい",  "group": "EV"},
]

# =============================================================================
# EC キーワード → 新 Need マッピング（優先度順）
# =============================================================================
EC_TO_NEW_NEEDS: list[tuple[str, list[str]]] = [
    # ファミリー
    ("ChildSafety",            ["子供の安全", "チャイルドシート", "後席安全", "キッズ安全", "子供を安全"]),
    ("EasyChildPickup",        ["乗せ降ろし", "子供の乗降", "チャイルドシート装着", "スライドドア"]),
    ("FamilyConversation",     ["家族で会話", "ファミリー空間", "会話しやすい"]),
    ("LargeCargoForFamily",    ["ベビーカー", "乳母車", "ベビー用品", "家族の荷物"]),
    ("WeekendFamilyTrip",      ["家族旅行", "ドライブ旅行", "週末旅行"]),
    ("ChildMonitoringEase",    ["後席確認", "子供の様子", "ルームミラー", "後席モニタ"]),
    ("StressFreeSchoolPickup", ["送迎", "学校", "幼稚園", "塾", "習い事の送迎"]),
    ("PetFriendlyTravel",      ["ペット", "愛犬", "犬", "猫", "動物"]),
    ("FamilyComfort",          ["家族全員", "ファミリー快適", "みんなが快適"]),
    # 安全
    ("EasyParking",              ["駐車", "バックカメラ", "パーキングセンサー", "駐車支援", "縦列駐車", "立体駐車"]),
    ("VisibilityConfidence",     ["視界", "見やすい", "周囲確認", "バックモニター", "全周囲"]),
    ("AccidentAnxietyReduction", ["事故不安", "衝突", "Honda SENSING", "緊急ブレーキ", "追突防止", "衝突軽減"]),
    ("NightDrivingConfidence",   ["夜間", "夜道", "暗い道", "LEDライト", "ハイビーム"]),
    ("SnowDrivingConfidence",    ["雪道", "雪", "凍結", "4WD", "AWD", "スリップ", "冬道"]),
    ("BeginnerFriendlyDriving", ["初心者", "ペーパードライバー", "扱いやすい", "運転しやすい"]),
    ("ElderlyDrivingSupport",    ["高齢", "シニア", "年配", "高齢者の運転", "親の運転"]),
    ("DrivingConfidence",        ["運転不安", "安心して運転", "運転が苦手", "自信がない"]),
    # 快適
    ("FatigueReduction",              ["疲れない", "疲労軽減", "長距離疲労", "腰への負担", "ドライバー疲労"]),
    ("QuietCabinExperience",          ["静か", "静粛性", "騒音", "防音", "NVH", "ロードノイズ"]),
    ("SmoothRideComfort",             ["乗り心地", "柔らかい乗り", "段差", "サスペンション", "振動が少ない"]),
    ("StressFreeCommute",             ["通勤", "毎日の移動", "渋滞ストレス", "通勤渋滞"]),
    ("RelaxingDrive",                 ["リラックス", "気持ちよく走る", "ゆったり", "余裕ある運転"]),
    ("ComfortableLongDistanceTravel", ["長距離", "高速道路", "遠出", "ロングドライブ", "長時間移動"]),
    ("ClimateComfort",                ["エアコン", "車内温度", "シートヒーター", "暖かい", "涼しい", "冷暖房"]),
    # 荷物
    ("FlexibleCargoSpace",       ["荷物が多い", "積載量", "荷室容量", "収納力"]),
    ("OutdoorGearTransport",     ["アウトドア用品", "キャンプ道具", "サーフボード", "スキー板", "自転車"]),
    ("EasyLoading",              ["積み下ろし", "テールゲート", "開口部が広い", "積みやすい"]),
    ("LargeShoppingCapacity",    ["まとめ買い", "スーパーの荷物", "買い物が多い", "大量購入"]),
    ("SportsEquipmentTransport", ["ゴルフ用品", "野球道具", "サッカー", "スポーツバッグ"]),
    ("FlatSeatUtility",          ["車中泊", "フルフラット", "シートアレンジ", "マジックシート"]),
    # 経済
    ("LowFuelAnxiety",           ["燃料代", "ガソリン代", "燃費不安", "給油頻度", "燃費向上"]),
    ("MaintenanceCostReduction", ["維持費", "メンテナンス費用", "修理費", "保険料", "税金"]),
    ("LongTermReliability",      ["長く乗る", "耐久性", "信頼性", "壊れない", "10年乗る"]),
    ("ResaleValueRetention",     ["リセール", "下取り価格", "売却価値", "資産価値"]),
    ("EfficientDailyMobility",   ["コスパ", "経済的", "お得", "日常移動コスト"]),
    # ライフスタイル
    ("DrivingEnjoyment",     ["運転を楽しむ", "走り", "スポーティな走り", "エンジン音", "走行性能"]),
    ("AdventureLifestyle",   ["冒険", "非日常", "探検"]),
    ("OutdoorLifestyle",     ["アウトドア", "キャンプ", "自然", "オフロード", "山道"]),
    ("EmotionalAttachment",  ["愛着", "一目惚れ", "ずっと乗りたい", "憧れ", "特別な車"]),
    ("PersonalExpression",   ["個性", "自分らしさ", "こだわり", "オリジナル", "カスタム"]),
    ("PremiumFeeling",       ["上質", "高級感", "プレミアム", "洗練", "品質感"]),
    ("ExcitingAcceleration", ["加速", "ターボ", "パワー", "スポーツ走行", "0-100"]),
    ("StatusRecognition",    ["かっこいい", "ステータス", "周囲の反応", "目立つ", "見た目が大事"]),
    # 都市
    ("UrbanManeuverability", ["狭い道", "取り回し", "小回り", "裏道", "路地"]),
    ("CompactParkingEase",   ["立体駐車場", "コンパクトカー", "全長が短い", "全幅が小さい"]),
    ("ShortTripEfficiency",  ["近距離", "ちょっとした移動", "日常の足"]),
    ("QuickErrandMobility",  ["お使い", "買い物", "ちょっと出かける"]),
    # アクセシビリティ
    ("EasyEntryExit",     ["乗り降り", "乗降しやすい", "足腰", "ステップが低い", "開口が広い"]),
    ("LowPhysicalBurden", ["身体負担", "腰への負担", "楽に乗れる", "体が楽"]),
    ("AccessibleSeating", ["座りやすい", "着座位置", "シート高さ", "ヒップポイント"]),
    ("CaregiverSupport",  ["介護", "車椅子", "お年寄り", "高齢者対応", "福祉"]),
    # EV・環境
    ("EnvironmentalResponsibility", ["環境配慮", "エコ", "CO2削減", "カーボンニュートラル", "地球環境"]),
    ("ChargingConfidence",          ["充電", "航続距離", "充電スポット", "EV不安", "急速充電"]),
    ("QuietElectricExperience",     ["EVの静かさ", "電気自動車", "モーター駆動", "電動の静粛性"]),
    ("EnergyEfficiency",            ["エネルギー効率", "回生ブレーキ", "電費", "ハイブリッド効率"]),
]

# =============================================================================
# 旧 Need（抽象カテゴリ）→ 新 Need（生活欲求）フォールバックマッピング
# EC キーワードでマッチしなかった場合に使用
# =============================================================================
OLD_TO_NEW_NEEDS: dict[str, list[str]] = {
    "safety":           ["DrivingConfidence", "AccidentAnxietyReduction", "EasyParking", "VisibilityConfidence"],
    "family":           ["FamilyComfort", "ChildSafety", "WeekendFamilyTrip", "StressFreeSchoolPickup"],
    "comfort":          ["FatigueReduction", "SmoothRideComfort", "RelaxingDrive", "QuietCabinExperience"],
    "space":            ["FlexibleCargoSpace", "FlatSeatUtility", "EasyLoading"],
    "fuel_efficiency":  ["LowFuelAnxiety", "EfficientDailyMobility", "EnergyEfficiency"],
    "economy":          ["LowFuelAnxiety", "MaintenanceCostReduction", "EfficientDailyMobility"],
    "performance":      ["DrivingEnjoyment", "ExcitingAcceleration"],
    "reliability":      ["LongTermReliability", "MaintenanceCostReduction"],
    "quality":          ["LongTermReliability", "PremiumFeeling"],
    "cost":             ["LowFuelAnxiety", "MaintenanceCostReduction", "EfficientDailyMobility"],
    "maintenance_cost": ["MaintenanceCostReduction", "LongTermReliability"],
    "price":            ["EfficientDailyMobility", "LowFuelAnxiety"],
    "affordability":    ["EfficientDailyMobility", "LongTermReliability"],
    "brand_loyalty":    ["EmotionalAttachment", "LongTermReliability"],
    "design":           ["PersonalExpression", "EmotionalAttachment", "PremiumFeeling"],
    "technology":       ["DrivingConfidence", "AccidentAnxietyReduction", "EasyParking"],
    "offroad":          ["OutdoorLifestyle", "AdventureLifestyle", "SnowDrivingConfidence"],
    "leisure":          ["OutdoorLifestyle", "DrivingEnjoyment", "WeekendFamilyTrip"],
    "lifestyle_change": ["PersonalExpression", "AdventureLifestyle", "EmotionalAttachment"],
    "nostalgia":        ["EmotionalAttachment"],
    "rarity":           ["PersonalExpression", "StatusRecognition"],
    "child_friendly":   ["ChildSafety", "EasyChildPickup", "FamilyComfort"],
}

# =============================================================================
# Capability → 新 Need マッピング
# =============================================================================
CAPABILITY_TO_NEW_NEEDS: dict[str, list[str]] = {
    "SafetyPerformance": [
        "AccidentAnxietyReduction", "DrivingConfidence", "EasyParking",
        "VisibilityConfidence", "NightDrivingConfidence", "SnowDrivingConfidence",
        "BeginnerFriendlyDriving", "ElderlyDrivingSupport", "ChildSafety",
    ],
    "FuelEfficiency": [
        "LowFuelAnxiety", "EfficientDailyMobility", "MaintenanceCostReduction",
        "EnergyEfficiency", "EnvironmentalResponsibility",
    ],
    "DesignAppeal": [
        "PersonalExpression", "EmotionalAttachment", "PremiumFeeling", "StatusRecognition",
    ],
    "TechInnovation": [
        "DrivingConfidence", "AccidentAnxietyReduction", "ChargingConfidence",
        "VisibilityConfidence", "EasyParking",
    ],
    "SpaceUtility": [
        "FlexibleCargoSpace", "LargeCargoForFamily", "EasyLoading", "FlatSeatUtility",
        "OutdoorGearTransport", "SportsEquipmentTransport", "LargeShoppingCapacity",
    ],
    "RideComfort": [
        "FatigueReduction", "QuietCabinExperience", "SmoothRideComfort",
        "RelaxingDrive", "ComfortableLongDistanceTravel", "ClimateComfort", "StressFreeCommute",
    ],
    "FamilyFriendly": [
        "ChildSafety", "EasyChildPickup", "FamilyConversation", "FamilyComfort",
        "LargeCargoForFamily", "WeekendFamilyTrip", "ChildMonitoringEase",
        "StressFreeSchoolPickup", "PetFriendlyTravel",
    ],
    "OffRoadCapability": [
        "OutdoorLifestyle", "AdventureLifestyle", "OutdoorGearTransport",
        "SnowDrivingConfidence",
    ],
    "GeneralPerformance": [
        "DrivingEnjoyment", "ExcitingAcceleration", "LongTermReliability",
        "EfficientDailyMobility",
    ],
}


def step5_1_create_new_needs(session):
    """新 Need ノード（55件）を作成"""
    print("\n--- Step 5-1: 新 Need ノード作成 ---")
    for need in NEW_NEED_MASTER:
        session.run("""
            MERGE (n:Need {name: $name})
            SET n.label = $label,
                n.group = $group,
                n.level = 'life_desire'
        """, name=need["name"], label=need["label"], group=need["group"])
    print(f"  → {len(NEW_NEED_MASTER)} 件の新 Need ノード作成")


def step5_2_migrate_consumer_needs(session):
    """Consumer の HAS_NEED を旧抽象カテゴリから新生活欲求 Need に移行"""
    print("\n--- Step 5-2: Consumer -[HAS_NEED]-> NewNeed 導出 ---")

    # 全消費者の旧 Need + EC を取得
    rows = session.run("""
        MATCH (c:Consumer)
        OPTIONAL MATCH (c)-[:HAS_NEED]->(on:Need)
            WHERE on.level <> 'life_desire' OR on.level IS NULL
        OPTIONAL MATCH (c)-[:VALUED]->(ec:EvaluationCriteria)
        RETURN c.id AS cid,
               collect(DISTINCT on.name) AS old_needs,
               collect(DISTINCT ec.name) AS ec_names
    """).data()

    total_new_rels = 0
    for row in rows:
        cid       = row["cid"]
        old_needs = [n for n in (row["old_needs"] or []) if n]
        ec_names  = [e for e in (row["ec_names"] or []) if e]

        # EC キーワードマッチで新 Need を導出
        new_needs: set[str] = set()
        ec_text = " ".join(ec_names)
        for need_name, keywords in EC_TO_NEW_NEEDS:
            if any(kw in ec_text for kw in keywords):
                new_needs.add(need_name)

        # 旧 Need → 新 Need フォールバックマッピング
        for old_need in old_needs:
            for new_need in OLD_TO_NEW_NEEDS.get(old_need, []):
                new_needs.add(new_need)

        # EC キーワードでも旧Needマッピングでも何も取れなかった場合
        if not new_needs:
            new_needs.add("EfficientDailyMobility")  # デフォルト

        # Neo4j に書き込み
        for need_name in new_needs:
            session.run("""
                MATCH (c:Consumer {id: $cid})
                MATCH (n:Need {name: $need_name})
                MERGE (c)-[:HAS_NEED]->(n)
            """, cid=cid, need_name=need_name)
        total_new_rels += len(new_needs)

    print(f"  → {len(rows)} 件の Consumer に合計 {total_new_rels} 件の HAS_NEED を設定")


def step5_3_update_capability_supports(session):
    """Capability -[SUPPORTS]-> Need を新 Need に再構築"""
    print("\n--- Step 5-3: Capability -[SUPPORTS]-> NewNeed 再構築 ---")

    # 旧 SUPPORTS を削除
    r = session.run("MATCH ()-[s:SUPPORTS]->() DELETE s RETURN count(s) AS cnt").single()
    print(f"  旧 SUPPORTS 削除: {r['cnt']} 件")

    # 新 SUPPORTS 作成
    total = 0
    for cap_name, need_names in CAPABILITY_TO_NEW_NEEDS.items():
        for need_name in need_names:
            r = session.run("""
                MATCH (cap:Capability {name: $cap_name})
                MATCH (n:Need {name: $need_name})
                MERGE (cap)-[s:SUPPORTS]->(n)
                RETURN count(s) AS cnt
            """, cap_name=cap_name, need_name=need_name).single()
            if r and r["cnt"]:
                total += r["cnt"]
    print(f"  新 SUPPORTS 作成: {total} 件")


def step5_4_delete_old_needs(session):
    """旧 Consumer -[HAS_NEED]-> OldNeed（抽象カテゴリ）を削除し旧 Need ノードを削除"""
    print("\n--- Step 5-4: 旧 Need ノード・リレーション削除 ---")

    # 旧 Need = level が 'life_desire' でないもの（または level が NULL）
    r = session.run("""
        MATCH (c:Consumer)-[hn:HAS_NEED]->(n:Need)
        WHERE n.level IS NULL OR n.level <> 'life_desire'
        DELETE hn
        RETURN count(hn) AS cnt
    """).single()
    print(f"  旧 HAS_NEED 削除: {r['cnt']} 件")

    # HAS_SUB_NEED も削除
    r2 = session.run("MATCH ()-[s:HAS_SUB_NEED]->() DELETE s RETURN count(s) AS cnt").single()
    print(f"  HAS_SUB_NEED 削除: {r2['cnt']} 件")

    # 旧 Need ノード（level が life_desire でないもの）を削除
    r3 = session.run("""
        MATCH (n:Need)
        WHERE n.level IS NULL OR n.level <> 'life_desire'
        DETACH DELETE n
        RETURN count(n) AS cnt
    """).single()
    print(f"  旧 Need ノード削除: {r3['cnt']} 件")


def verify(session):
    print("\n--- 検証 ---")
    r = session.run("MATCH (n:Need) RETURN n.group AS grp, count(*) AS cnt ORDER BY grp").data()
    print("  新 Need グループ分布:")
    for row in r:
        print(f"    {row['grp']:<15}: {row['cnt']} 件")

    r2 = session.run("MATCH ()-[h:HAS_NEED]->() RETURN count(h) AS cnt").single()
    print(f"  HAS_NEED 合計: {r2['cnt']} 件")

    r3 = session.run("""
        MATCH (c:Consumer)-[:HAS_NEED]->(n:Need)
        RETURN n.name AS need, count(c) AS cnt
        ORDER BY cnt DESC LIMIT 15
    """).data()
    print("  上位 Need（Consumer数）:")
    for row in r3:
        print(f"    {row['need']:<35}: {row['cnt']} 件")

    r4 = session.run("MATCH (cap:Capability)-[:SUPPORTS]->(n:Need) RETURN cap.label AS cap, count(n) AS cnt ORDER BY cnt DESC").data()
    print("  Capability -[SUPPORTS]-> Need 件数:")
    for row in r4:
        print(f"    {row['cap']:<20}: {row['cnt']} 件")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        step5_1_create_new_needs(session)
        step5_2_migrate_consumer_needs(session)
        step5_3_update_capability_supports(session)
        step5_4_delete_old_needs(session)
        verify(session)
    driver.close()
    print("\n✅ Step 5 (Need 再設計) 完了")


if __name__ == "__main__":
    main()
