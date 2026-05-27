"""
update_ontology_v3_step4.py
---------------------------
Step 4: 残りプロパティの追加

  4-1. Need.label                    22件 → 日本語ラベル（ハードコード）
  4-2. PurchaseDriver.label          11件 → 英語コード（ハードコード）
  4-3. EvaluationCriteria.label    5046件 → Capability名 (INFLUENCES接続 or キーワード)
  4-4. Consumer.household_vehicle_count → ストーリーテキストからルールベース抽出

今後の再構築用ルール定義もこのファイルに集約。
"""
import os, sys, io, json, re
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from neo4j import GraphDatabase

NEO4J_URI      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "KMixerOrigin2026")

STORIES_PATH   = Path("data/raw/consumer_stories.json")

# =============================================================================
# ルール定義（今後の再構築でも同じルールを使用）
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# [RULE-NEED-LABEL] Need.name → Need.label（日本語）
# ─────────────────────────────────────────────────────────────────────────────
NEED_LABELS = {
    "safety":           "安全性",
    "family":           "家族対応",
    "comfort":          "快適性",
    "space":            "空間・広さ",
    "design":           "デザイン",
    "technology":       "技術・機能",
    "fuel_efficiency":  "燃費",
    "economy":          "経済性",
    "performance":      "走行性能",
    "reliability":      "信頼性・耐久性",
    "quality":          "品質",
    "cost":             "コスト",
    "maintenance_cost": "維持費",
    "price":            "価格",
    "affordability":    "コストパフォーマンス",
    "brand_loyalty":    "ブランドへの愛着",
    "offroad":          "オフロード性能",
    "leisure":          "レジャー・趣味",
    "lifestyle_change": "ライフスタイル変化",
    "nostalgia":        "ノスタルジア",
    "rarity":           "希少性・個性",
    "child_friendly":   "子供対応",
}

# ─────────────────────────────────────────────────────────────────────────────
# [RULE-PD-LABEL] PurchaseDriver.name → PurchaseDriver.label（英語コード）
# ─────────────────────────────────────────────────────────────────────────────
PURCHASE_DRIVER_LABELS = {
    "安全性能":       "safety_performance",
    "燃費・維持費":   "fuel_economy",
    "広さ・実用性":   "practicality",
    "デザイン・スタイル": "design_style",
    "ブランド・信頼性":  "brand_trust",
    "乗り心地・快適性":  "ride_comfort",
    "価格・コスパ":    "price_value",
    "先進技術・装備":  "tech_equipment",
    "家族・他者の意見": "social_influence",
    "試乗体験":       "test_drive_experience",
    "その他":         "other",
}

# ─────────────────────────────────────────────────────────────────────────────
# [RULE-EC-LABEL] EvaluationCriteria キーワード → Capability名
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
    """EvaluationCriteria.name からラベルを分類するルール関数"""
    for cap_name, keywords in EC_LABEL_KEYWORDS:
        for kw in keywords:
            if kw in name:
                return cap_name
    return EC_LABEL_DEFAULT

# ─────────────────────────────────────────────────────────────────────────────
# [RULE-VEHICLE-COUNT] household_vehicle_count 抽出パターン
# ─────────────────────────────────────────────────────────────────────────────
VEHICLE_COUNT_PATTERNS = [
    re.compile(r'(\d)\s*台\s*(所有|持ち|保有)'),  # 「2台所有」「2台持ち」
    re.compile(r'(計|合計)\s*(\d)\s*台'),          # 「計2台」
    re.compile(r'世帯\s*(\d)\s*台'),               # 「世帯2台」
    re.compile(r'家\s*に\s*(\d)\s*台'),            # 「家に2台」
    re.compile(r'一家に(\d)\s*台'),                # 「一家に2台」
]

def extract_vehicle_count(story_text: str) -> int | None:
    """ストーリーテキストから世帯保有台数をルールで抽出する"""
    text = str(story_text)
    for pattern in VEHICLE_COUNT_PATTERNS:
        m = pattern.search(text)
        if m:
            # 数字グループを探す
            for g in m.groups():
                if g and g.isdigit():
                    return int(g)
    return None


# =============================================================================
# 実装
# =============================================================================

def step4_1_need_labels(session):
    print("\n--- Step 4-1: Need.label 追加 ---")
    updated = 0
    for name, label in NEED_LABELS.items():
        r = session.run(
            "MATCH (n:Need {name: $name}) SET n.label = $label RETURN n.name",
            name=name, label=label
        ).data()
        if r:
            updated += 1
    print(f"  → {updated} / {len(NEED_LABELS)} 件更新")
    # 確認
    rows = session.run(
        "MATCH (n:Need) RETURN n.name AS name, n.label AS label ORDER BY n.name"
    ).data()
    for r in rows:
        print(f"    {r['name']:<20} → {r['label']}")


def step4_2_purchase_driver_labels(session):
    print("\n--- Step 4-2: PurchaseDriver.label 追加 ---")
    updated = 0
    for name, label in PURCHASE_DRIVER_LABELS.items():
        r = session.run(
            "MATCH (pd:PurchaseDriver {name: $name}) SET pd.label = $label RETURN pd.name",
            name=name, label=label
        ).data()
        if r:
            updated += 1
    print(f"  → {updated} / {len(PURCHASE_DRIVER_LABELS)} 件更新")
    rows = session.run(
        "MATCH (pd:PurchaseDriver) RETURN pd.name AS name, pd.label AS label ORDER BY pd.label"
    ).data()
    for r in rows:
        print(f"    {r['name']:<20} → {r['label']}")


def step4_3_ec_labels(session):
    print("\n--- Step 4-3: EvaluationCriteria.label 追加 ---")

    # Step A: INFLUENCES 接続がある EC → 接続 Capability 名を label に使用
    # （複数接続がある場合は最初のCapabilityを採用）
    result_a = session.run(
        """
        MATCH (cap:Capability)-[:INFLUENCES]->(ec:EvaluationCriteria)
        WHERE ec.label IS NULL
        WITH ec, collect(cap.name) AS caps
        SET ec.label = caps[0]
        RETURN count(ec) AS cnt
        """
    ).single()
    cnt_a = result_a["cnt"] if result_a else 0
    print(f"  INFLUENCES接続あり: {cnt_a} 件を設定")

    # Step B: INFLUENCES 接続がない EC → キーワードルールで分類
    rows = session.run(
        "MATCH (ec:EvaluationCriteria) WHERE ec.label IS NULL RETURN ec.id AS id, ec.name AS name"
    ).data()
    cnt_b = 0
    for row in rows:
        label = classify_ec_label(row["name"] or "")
        session.run(
            "MATCH (ec:EvaluationCriteria {id: $id}) SET ec.label = $label",
            id=row["id"], label=label
        )
        cnt_b += 1
    print(f"  キーワードルール: {cnt_b} 件を設定")

    # 分布確認
    dist = session.run(
        "MATCH (ec:EvaluationCriteria) RETURN ec.label AS label, count(*) AS cnt ORDER BY cnt DESC"
    ).data()
    print("  label 分布:")
    for d in dist:
        lbl = d['label'] or '(null)'
        print(f"    {lbl:<30} {d['cnt']:>5} 件")


def step4_4_household_vehicle_count(session):
    print("\n--- Step 4-4: Consumer.household_vehicle_count 追加 ---")

    if not STORIES_PATH.exists():
        print("  [SKIP] stories ファイルが見つかりません")
        return

    stories = json.loads(STORIES_PATH.read_text(encoding="utf-8"))
    found = 0
    for story in stories:
        count = extract_vehicle_count(str(story.get("story_text", "")))
        if count is not None:
            session.run(
                "MATCH (c:Consumer {id: $sid}) SET c.household_vehicle_count = $cnt",
                sid=story["story_id"], cnt=count
            )
            found += 1

    total = len(stories)
    print(f"  → {found} / {total} 件で抽出成功（残り {total-found} 件は null）")

    # 分布
    dist = session.run(
        "MATCH (c:Consumer) WHERE c.household_vehicle_count IS NOT NULL "
        "RETURN c.household_vehicle_count AS cnt, count(*) AS num ORDER BY cnt"
    ).data()
    print("  household_vehicle_count 分布:")
    for d in dist:
        print(f"    {d['cnt']}台: {d['num']} 件")


def verify(session):
    print("\n--- 最終グラフ統計 ---")
    node_labels = [
        "Consumer", "VehicleModel", "VehicleOwnership", "Outcome", "Regret",
        "Need", "EvaluationCriteria", "PurchaseDriver",
        "TechnicalFeature", "Capability",
        "DecisionStyle", "LifeEvent", "Trigger", "Feature"
    ]
    print("  Nodes:")
    for label in node_labels:
        r = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt").single()
        cnt = r["cnt"] if r else 0
        if cnt > 0:
            print(f"    {label:<25}: {cnt:>6}")

    rel_types = [
        "OWNED", "OF_MODEL", "HAS_DECISION_STYLE", "EXPERIENCED", "HAS_TRIGGER",
        "HAS_NEED", "VALUED", "DECIDED", "CONSIDERED",
        "RESULTED_IN", "CAUSED_REGRET",
        "HAS_FEATURE", "REALIZES", "SUPPORTS", "INFLUENCES", "REDUCES", "APPEALS_TO",
        "HAS_SUB_NEED",
    ]
    print("  Relationships:")
    for rel in rel_types:
        r = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS cnt").single()
        cnt = r["cnt"] if r else 0
        if cnt > 0:
            print(f"    {rel:<25}: {cnt:>6}")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        step4_1_need_labels(session)
        step4_2_purchase_driver_labels(session)
        step4_3_ec_labels(session)
        step4_4_household_vehicle_count(session)
        verify(session)
    driver.close()
    print("\n✅ Step 4 完了")


if __name__ == "__main__":
    main()
