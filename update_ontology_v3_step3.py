"""
update_ontology_v3_step3.py
---------------------------
Step 3: Feature ノードを TechnicalFeature + Capability に分割

処理内容:
  1. Feature ノードに :TechnicalFeature ラベルを追加 → :Feature ラベルを削除
  2. Capability ノード 9件 を新規作成
  3. TechnicalFeature -[REALIZES]-> Capability（category 基準）
  4. Capability -[SUPPORTS]-> Need
  5. Capability -[INFLUENCES]-> EvaluationCriteria（旧 MAPS_TO を流用）
  6. Capability -[REDUCES]-> Regret
  7. Capability -[APPEALS_TO]-> DecisionStyle
  8. 旧リレーション削除: MAPS_TO(31786), MEETS(24011), SATISFIES(166)
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from neo4j import GraphDatabase

NEO4J_URI      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "KMixerOrigin2026")

# ─────────────────────────────────────────────────────────────────────────────
# Capability マスタ（category → Capability の対応）
# ─────────────────────────────────────────────────────────────────────────────
CAPABILITY_MASTER = [
    {
        "name":        "SafetyPerformance",
        "label":       "安全性能",
        "description": "衝突回避・被害軽減・乗員保護に関わる総合安全能力",
        "category":    "safety",
    },
    {
        "name":        "FuelEfficiency",
        "label":       "燃費・エネルギー効率",
        "description": "燃料消費の低減・電動化によるエネルギー最適化能力",
        "category":    "fuel_efficiency",
    },
    {
        "name":        "DesignAppeal",
        "label":       "デザイン魅力",
        "description": "外観・内装の美しさ・個性・ブランドイメージの訴求力",
        "category":    "design",
    },
    {
        "name":        "TechInnovation",
        "label":       "先進技術",
        "description": "コネクテッド・自動化・デジタル化による利便性・体験向上",
        "category":    "technology",
    },
    {
        "name":        "SpaceUtility",
        "label":       "空間・収納",
        "description": "室内空間の広さ・荷物収納・シートアレンジの柔軟性",
        "category":    "space",
    },
    {
        "name":        "RideComfort",
        "label":       "快適・静粛性",
        "description": "乗り心地・静粛性・疲労軽減・ドライビングポジションの快適さ",
        "category":    "comfort",
    },
    {
        "name":        "FamilyFriendly",
        "label":       "ファミリー対応",
        "description": "子供・家族の乗降・チャイルドシート・後席快適性への対応",
        "category":    "family",
    },
    {
        "name":        "OffRoadCapability",
        "label":       "オフロード・走破性",
        "description": "悪路・雪道・山道など非舗装路での走行安定性・牽引能力",
        "category":    "offroad",
    },
    {
        "name":        "GeneralPerformance",
        "label":       "総合性能",
        "description": "走行性能・信頼性・コストパフォーマンスを含む総合的な車両能力",
        "category":    "general",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Capability → Need マッピング（複数対応）
# ─────────────────────────────────────────────────────────────────────────────
CAPABILITY_TO_NEEDS = {
    "SafetyPerformance":  ["safety", "reliability", "quality"],
    "FuelEfficiency":     ["fuel_efficiency", "economy", "maintenance_cost", "cost"],
    "DesignAppeal":       ["design", "lifestyle_change", "rarity"],
    "TechInnovation":     ["technology", "performance"],
    "SpaceUtility":       ["space", "family", "child_friendly"],
    "RideComfort":        ["comfort", "quality", "reliability"],
    "FamilyFriendly":     ["family", "child_friendly", "safety"],
    "OffRoadCapability":  ["offroad", "leisure", "performance"],
    "GeneralPerformance": ["performance", "reliability", "quality", "affordability"],
}

# ─────────────────────────────────────────────────────────────────────────────
# Capability → Regret（軽減する後悔）マッピング
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# Capability → DecisionStyle マッピング
# ─────────────────────────────────────────────────────────────────────────────
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


def step3_relabel_features(session):
    """Feature → TechnicalFeature に re-label"""
    print("\n--- Step 3-1: Feature → TechnicalFeature 再ラベル ---")
    result = session.run(
        "MATCH (f:Feature) SET f:TechnicalFeature REMOVE f:Feature RETURN count(f) AS cnt"
    )
    cnt = result.single()["cnt"]
    print(f"  → {cnt} 件を TechnicalFeature に変換")


def step3_create_capabilities(session):
    """Capability ノードを新規作成"""
    print("\n--- Step 3-2: Capability ノード作成 ---")
    for cap in CAPABILITY_MASTER:
        session.run(
            """
            MERGE (c:Capability {name: $name})
            SET c.label       = $label,
                c.description = $description,
                c.category    = $category
            """,
            name=cap["name"], label=cap["label"],
            description=cap["description"], category=cap["category"]
        )
        print(f"  ✓ {cap['name']} ({cap['label']})")
    print(f"  → {len(CAPABILITY_MASTER)} 件作成完了")


def step3_realizes(session):
    """TechnicalFeature -[REALIZES]-> Capability（category 基準）"""
    print("\n--- Step 3-3: TechnicalFeature -[REALIZES]-> Capability ---")
    result = session.run(
        """
        MATCH (tf:TechnicalFeature)
        MATCH (cap:Capability {category: tf.category})
        MERGE (tf)-[r:REALIZES]->(cap)
        RETURN count(r) AS cnt
        """
    )
    cnt = result.single()["cnt"]
    print(f"  → {cnt} 件の REALIZES リレーション作成")


def step3_supports_need(session):
    """Capability -[SUPPORTS]-> Need"""
    print("\n--- Step 3-4: Capability -[SUPPORTS]-> Need ---")
    total = 0
    for cap_name, need_names in CAPABILITY_TO_NEEDS.items():
        for need_name in need_names:
            result = session.run(
                """
                MATCH (cap:Capability {name: $cap_name})
                MATCH (n:Need {name: $need_name})
                MERGE (cap)-[r:SUPPORTS]->(n)
                RETURN count(r) AS cnt
                """,
                cap_name=cap_name, need_name=need_name
            )
            row = result.single()
            if row and row["cnt"] > 0:
                total += row["cnt"]
    print(f"  → {total} 件の SUPPORTS リレーション作成")


def step3_influences_ec(session):
    """Capability -[INFLUENCES]-> EvaluationCriteria（旧 MAPS_TO の接続先 Feature.category を利用）"""
    print("\n--- Step 3-5: Capability -[INFLUENCES]-> EvaluationCriteria ---")
    # 旧 MAPS_TO: EvaluationCriteria -> Feature（現 TechnicalFeature）
    # Feature.category から Capability を特定して逆方向に接続
    result = session.run(
        """
        MATCH (ec:EvaluationCriteria)-[:MAPS_TO]->(tf:TechnicalFeature)
        MATCH (cap:Capability {category: tf.category})
        MERGE (cap)-[r:INFLUENCES]->(ec)
        RETURN count(r) AS cnt
        """
    )
    cnt = result.single()["cnt"]
    print(f"  → {cnt} 件の INFLUENCES リレーション作成")


def step3_reduces_regret(session):
    """Capability -[REDUCES]-> Regret"""
    print("\n--- Step 3-6: Capability -[REDUCES]-> Regret ---")
    total = 0
    for cap_name, regret_names in CAPABILITY_TO_REGRETS.items():
        for regret_name in regret_names:
            result = session.run(
                """
                MATCH (cap:Capability {name: $cap_name})
                MATCH (r:Regret {name: $regret_name})
                MERGE (cap)-[rel:REDUCES]->(r)
                RETURN count(rel) AS cnt
                """,
                cap_name=cap_name, regret_name=regret_name
            )
            row = result.single()
            if row and row["cnt"] > 0:
                total += row["cnt"]
    print(f"  → {total} 件の REDUCES リレーション作成")


def step3_appeals_to_decision_style(session):
    """Capability -[APPEALS_TO]-> DecisionStyle"""
    print("\n--- Step 3-7: Capability -[APPEALS_TO]-> DecisionStyle ---")
    total = 0
    for cap_name, style_names in CAPABILITY_TO_DECISION_STYLES.items():
        for style_name in style_names:
            result = session.run(
                """
                MATCH (cap:Capability {name: $cap_name})
                MATCH (d:DecisionStyle {name: $style_name})
                MERGE (cap)-[r:APPEALS_TO]->(d)
                RETURN count(r) AS cnt
                """,
                cap_name=cap_name, style_name=style_name
            )
            row = result.single()
            if row and row["cnt"] > 0:
                total += row["cnt"]
    print(f"  → {total} 件の APPEALS_TO リレーション作成")


def step3_delete_old_rels(session):
    """旧リレーション削除: MAPS_TO / MEETS / SATISFIES（バッチ削除）"""
    print("\n--- Step 3-8: 旧リレーション削除 ---")

    for rel_type in ["MAPS_TO", "MEETS", "SATISFIES"]:
        total_deleted = 0
        while True:
            result = session.run(
                f"MATCH ()-[r:{rel_type}]->() WITH r LIMIT 5000 DELETE r RETURN count(r) AS cnt"
            )
            cnt = result.single()["cnt"]
            total_deleted += cnt
            if cnt == 0:
                break
        print(f"  {rel_type}: {total_deleted} 件削除")


def verify(session):
    """最終検証"""
    print("\n--- 検証 ---")

    # ノード数
    for label in ["TechnicalFeature", "Capability", "Feature"]:
        r = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt").single()
        print(f"  {label}: {r['cnt']} 件")

    # リレーション数
    for rel in ["REALIZES", "SUPPORTS", "INFLUENCES", "REDUCES", "APPEALS_TO", "MAPS_TO", "MEETS"]:
        r = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS cnt").single()
        print(f"  {rel}: {r['cnt']} 件")

    # サンプル
    print("\n  サンプル: Capability -[SUPPORTS]-> Need")
    rows = session.run(
        "MATCH (c:Capability)-[:SUPPORTS]->(n:Need) RETURN c.label AS cap, n.name AS need ORDER BY c.name, n.name"
    ).data()
    for r in rows:
        print(f"    {r['cap']} → {r['need']}")

    print("\n  サンプル: TechnicalFeature -[REALIZES]-> Capability (各Capabilityの件数)")
    rows = session.run(
        "MATCH (tf:TechnicalFeature)-[:REALIZES]->(c:Capability) RETURN c.label AS cap, count(tf) AS cnt ORDER BY cnt DESC"
    ).data()
    for r in rows:
        print(f"    {r['cap']}: {r['cnt']} 件")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        step3_relabel_features(session)
        step3_create_capabilities(session)
        step3_realizes(session)
        step3_supports_need(session)
        step3_influences_ec(session)
        step3_reduces_regret(session)
        step3_appeals_to_decision_style(session)
        step3_delete_old_rels(session)
        verify(session)
    driver.close()
    print("\n✅ Step 3 完了")


if __name__ == "__main__":
    main()
