"""
update_ontology_v3_step1.py
---------------------------
Step 1a: DecisionStyle に decision_behavior / information_preference を追加
Step 1b: VehicleOwnership に vehicle_role を追加（usage_pattern から導出）
Step 1c: VehicleModel に segment / body_type / fuel_type / drive_type / seating_capacity を追加
"""
import os
from neo4j import GraphDatabase

NEO4J_URI      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "KMixerOrigin2026")

# ─────────────────────────────────────────────────────────────────────────────
# Step 1a: DecisionStyle マスタ定義
# ─────────────────────────────────────────────────────────────────────────────
DECISION_STYLE_MASTER = {
    "Maximizer": {
        "decision_behavior": [
            "compares_many_options", "seeks_best_choice", "avoids_regret",
            "long_decision_cycle", "research_driven", "sensitive_to_tradeoffs"
        ],
        "information_preference": [
            "comparison_table", "detailed_specification", "expert_review",
            "ranking", "ownership_cost_analysis", "competitive_comparison",
            "long_term_reliability_data"
        ]
    },
    "Satisficer": {
        "decision_behavior": [
            "sets_acceptance_threshold", "limits_option_comparison",
            "prioritizes_efficiency", "prefers_low_cognitive_load",
            "shortlist_oriented"
        ],
        "information_preference": [
            "recommended_package", "simple_comparison", "best_value_summary",
            "easy_to_understand_explanation", "popular_choice",
            "time_saving_information"
        ]
    },
    "Authority-driven": {
        "decision_behavior": [
            "trusts_experts", "follows_authoritative_opinion",
            "brand_reassurance_seeking", "risk_avoidant",
            "validates_with_external_authority"
        ],
        "information_preference": [
            "expert_opinion", "dealer_recommendation", "brand_history",
            "safety_awards", "professional_review", "certification",
            "customer_satisfaction_ranking"
        ]
    },
    "Delegator": {
        "decision_behavior": [
            "relies_on_recommendation", "outsources_evaluation",
            "avoids_detailed_analysis", "seeks_social_consensus",
            "decision_by_trusted_person"
        ],
        "information_preference": [
            "recommended_choice", "staff_pick", "family_feedback",
            "friend_usage_story", "popular_configuration", "best_seller",
            "easy_recommendation"
        ]
    },
    "Intuitive": {
        "decision_behavior": [
            "relies_on_feeling", "emotionally_driven",
            "instant_impression_sensitive", "experience_oriented",
            "visual_emphasis"
        ],
        "information_preference": [
            "visual_design", "test_drive_experience", "storytelling",
            "lifestyle_imagery", "emotional_message", "video_content",
            "owner_story"
        ]
    },
    "Impulsive": {
        "decision_behavior": [
            "fast_decision", "emotionally_reactive", "promotion_sensitive",
            "novelty_seeking", "low_deliberation"
        ],
        "information_preference": [
            "limited_offer", "discount_information", "immediate_availability",
            "campaign_message", "attention_grabbing_visual", "social_trend",
            "quick_summary"
        ]
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 1b: usage_pattern → vehicle_role マッピングルール
# （usage_pattern に該当キーワードが含まれれば対応する vehicle_role を付与）
# ─────────────────────────────────────────────────────────────────────────────
USAGE_TO_ROLE = [
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

# ─────────────────────────────────────────────────────────────────────────────
# Step 1c: VehicleModel マスタ定義
# 同一モデル名でも構成違い（例: FIT Gasoline vs FIT e:HEV）は別エントリ
# key = モデル名（Neo4jの v.name と一致させる）
# ─────────────────────────────────────────────────────────────────────────────
VEHICLE_MODEL_MASTER = {
    # ── FIT / フィット ────────────────────────────────────────────
    "FIT": {
        "segment": "B_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "フィット": {
        "segment": "B_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "フィット RS": {
        "segment": "B_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Performance"
    },
    "フィットシャトル": {
        "segment": "B_Segment", "body_type": "Wagon",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    # ── SHUTTLE ──────────────────────────────────────────────────
    "SHUTTLE": {
        "segment": "B_Segment", "body_type": "Wagon",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "フィット シャトル": {
        "segment": "B_Segment", "body_type": "Wagon",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    # ── ステップワゴン ────────────────────────────────────────────
    "ステップワゴン": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    "Honda Step WGN": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    "ステップワゴン RG1": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    # ── オデッセイ ────────────────────────────────────────────────
    "オデッセイ": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    "Honda Odyssey": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    "Honda ODYSSEY HYBRID ABSOLUTE": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    "ODYSSEY RA6": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    "エリシオン": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    # ── フリード ──────────────────────────────────────────────────
    "フリード": {
        "segment": "CompactMinivan", "body_type": "CompactVan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 6, "category": "Passenger"
    },
    "フリード スパイク": {
        "segment": "CompactMinivan", "body_type": "CompactVan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Utility"
    },
    "FREEDSPIKE": {
        "segment": "CompactMinivan", "body_type": "CompactVan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Utility"
    },
    "モビリオ": {
        "segment": "CompactMinivan", "body_type": "CompactVan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 7, "category": "Passenger"
    },
    "ジェイド": {
        "segment": "CompactMinivan", "body_type": "Wagon",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 6, "category": "Passenger"
    },
    "ストリーム": {
        "segment": "CompactMinivan", "body_type": "CompactVan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 7, "category": "Passenger"
    },
    # ── N-BOX ──────────────────────────────────────────────────
    "N-BOX": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "NBOXPLUS": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Utility"
    },
    "NBOXSLASH": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "N-BOX SLASH": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "N BOX": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    # ── その他 軽自動車 ─────────────────────────────────────────
    "N-ONE": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "N-WGN": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "ライフ": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "ゼスト": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "THATS": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "ホンダ ザッツ": {
        "segment": "Kei_Segment", "body_type": "KeiCar",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Passenger"
    },
    "VAMOS": {
        "segment": "Kei_Segment", "body_type": "KeiVan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Utility"
    },
    "N-VAN": {
        "segment": "Kei_Segment", "body_type": "KeiVan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Commercial"
    },
    "エアウェイブ": {
        "segment": "B_Segment", "body_type": "Wagon",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "エディックス": {
        "segment": "B_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 6, "category": "Passenger"
    },
    # ── CIVIC ──────────────────────────────────────────────────
    "CIVIC": {
        "segment": "C_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "CIVIC TYPE R": {
        "segment": "C_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Performance"
    },
    "シビックTYPE R": {
        "segment": "C_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Performance"
    },
    "シビック セダン": {
        "segment": "C_Segment", "body_type": "Sedan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "シビック ハッチバック": {
        "segment": "C_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "インテグラ": {
        "segment": "C_Segment", "body_type": "Sedan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Performance"
    },
    "インテグラ スポーツリミテッド": {
        "segment": "C_Segment", "body_type": "Sedan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Performance"
    },
    "PRELUDE": {
        "segment": "C_Segment", "body_type": "Coupe",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Performance"
    },
    "CR-X": {
        "segment": "B_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 2, "category": "Performance"
    },
    # ── ACCORD ─────────────────────────────────────────────────
    "ACCORD": {
        "segment": "D_Segment", "body_type": "Sedan",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "アコード": {
        "segment": "D_Segment", "body_type": "Sedan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "アコード ハイブリッド EX": {
        "segment": "D_Segment", "body_type": "Sedan",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Electrified"
    },
    "Honda アコードワゴン（2002年式）": {
        "segment": "D_Segment", "body_type": "Wagon",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "Honda Accord Wagon": {
        "segment": "D_Segment", "body_type": "Wagon",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "INSPIRE": {
        "segment": "D_Segment", "body_type": "Sedan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    # ── インサイト ────────────────────────────────────────────
    "インサイト": {
        "segment": "C_Segment", "body_type": "Sedan",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Electrified"
    },
    "GRACE": {
        "segment": "B_Segment", "body_type": "Sedan",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    # ── SUV ────────────────────────────────────────────────────
    "VEZEL": {
        "segment": "CompactSUV", "body_type": "CrossoverSUV",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "ヴェゼル": {
        "segment": "CompactSUV", "body_type": "CrossoverSUV",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "CR-V": {
        "segment": "MidSizeSUV", "body_type": "SUV",
        "fuel_type": "Gasoline", "drive_type": "4WD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "HR-V": {
        "segment": "CompactSUV", "body_type": "SUV",
        "fuel_type": "Gasoline", "drive_type": "4WD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "クロスロード": {
        "segment": "CompactSUV", "body_type": "OffRoadVehicle",
        "fuel_type": "Gasoline", "drive_type": "4WD",
        "seating_capacity": 5, "category": "Utility"
    },
    # ── スポーツ ────────────────────────────────────────────────
    "S660": {
        "segment": "Kei_Segment", "body_type": "Convertible",
        "fuel_type": "Gasoline", "drive_type": "MR",
        "seating_capacity": 2, "category": "Performance"
    },
    "Honda S660": {
        "segment": "Kei_Segment", "body_type": "Convertible",
        "fuel_type": "Gasoline", "drive_type": "MR",
        "seating_capacity": 2, "category": "Performance"
    },
    "S2000": {
        "segment": "D_Segment", "body_type": "Roadster",
        "fuel_type": "Gasoline", "drive_type": "FR",
        "seating_capacity": 2, "category": "Performance"
    },
    "S2000 TypeS": {
        "segment": "D_Segment", "body_type": "Roadster",
        "fuel_type": "Gasoline", "drive_type": "FR",
        "seating_capacity": 2, "category": "Performance"
    },
    "CR-Z": {
        "segment": "C_Segment", "body_type": "Coupe",
        "fuel_type": "Hybrid", "drive_type": "FWD",
        "seating_capacity": 4, "category": "Performance"
    },
    "NSX": {
        "segment": "E_Segment", "body_type": "Coupe",
        "fuel_type": "Hybrid", "drive_type": "AWD",
        "seating_capacity": 2, "category": "Performance"
    },
    # ── 高級 ────────────────────────────────────────────────────
    "LEGEND": {
        "segment": "E_Segment", "body_type": "Sedan",
        "fuel_type": "Hybrid", "drive_type": "AWD",
        "seating_capacity": 5, "category": "Luxury"
    },
    # ── 商用 ────────────────────────────────────────────────────
    "ACTY TRUCK": {
        "segment": "Kei_Segment", "body_type": "CommercialTruck",
        "fuel_type": "Gasoline", "drive_type": "FR",
        "seating_capacity": 2, "category": "Commercial"
    },
    # ── EV ─────────────────────────────────────────────────────
    "Honda e": {
        "segment": "B_Segment", "body_type": "Hatchback",
        "fuel_type": "Electric", "drive_type": "RWD",
        "seating_capacity": 4, "category": "Electrified"
    },
    # ── その他旧型 ──────────────────────────────────────────────
    "ホンダ・フィット（GD1後期）": {
        "segment": "B_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "2008年型 FIT（FF）": {
        "segment": "B_Segment", "body_type": "Hatchback",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 5, "category": "Passenger"
    },
    "ホンダ ストリーム RSZ": {
        "segment": "CompactMinivan", "body_type": "CompactVan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 7, "category": "Passenger"
    },
    "ステップワゴン RG1": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
    "RG1型ステップワゴン": {
        "segment": "LargeMinivan", "body_type": "Minivan",
        "fuel_type": "Gasoline", "drive_type": "FWD",
        "seating_capacity": 8, "category": "Passenger"
    },
}


def step1a_update_decision_styles(session):
    """DecisionStyle に decision_behavior / information_preference を追加"""
    print("\n--- Step 1a: DecisionStyle プロパティ追加 ---")
    updated = 0
    for name, props in DECISION_STYLE_MASTER.items():
        result = session.run(
            """
            MATCH (d:DecisionStyle {name: $name})
            SET d.decision_behavior      = $decision_behavior,
                d.information_preference = $information_preference
            RETURN d.name AS name
            """,
            name=name,
            decision_behavior=props["decision_behavior"],
            information_preference=props["information_preference"]
        )
        rows = result.data()
        if rows:
            print(f"  ✓ {name}")
            updated += 1
        else:
            print(f"  ✗ NOT FOUND: {name}")
    print(f"  → {updated} / {len(DECISION_STYLE_MASTER)} 件更新")


def step1b_update_vehicle_role(session):
    """VehicleOwnership に vehicle_role を追加（usage_pattern から導出）"""
    print("\n--- Step 1b: VehicleOwnership.vehicle_role 追加 ---")

    # 全 VehicleOwnership を取得して Python 側でロール判定
    result = session.run(
        "MATCH (vo:VehicleOwnership) RETURN vo.id AS id, vo.usage_pattern AS up, vo.is_current AS is_current"
    )
    rows = result.data()

    updated = 0
    for row in rows:
        up = (row["up"] or "").lower()
        roles = []
        for keyword, role in USAGE_TO_ROLE:
            if keyword in up:
                roles.append(role)
        if not roles:
            # usage_pattern 不明 → is_current ならメイン車扱い
            roles = ["PrimaryVehicle"] if row["is_current"] else ["SecondaryVehicle"]

        session.run(
            "MATCH (vo:VehicleOwnership {id: $id}) SET vo.vehicle_role = $roles",
            id=row["id"], roles=roles
        )
        updated += 1

    print(f"  → {updated} 件の vehicle_role を設定")

    # 分布確認
    dist_result = session.run(
        """
        MATCH (vo:VehicleOwnership)
        UNWIND vo.vehicle_role AS role
        RETURN role, count(*) AS cnt ORDER BY cnt DESC
        """
    )
    print("  vehicle_role 分布:")
    for r in dist_result.data():
        print(f"    {r['role']}: {r['cnt']}")


def step1c_update_vehicle_models(session):
    """VehicleModel に segment / body_type / fuel_type / drive_type / seating_capacity を追加"""
    print("\n--- Step 1c: VehicleModel プロパティ追加 ---")
    updated = 0
    not_found = []

    for name, props in VEHICLE_MODEL_MASTER.items():
        result = session.run(
            """
            MATCH (v:VehicleModel {name: $name})
            SET v.segment          = $segment,
                v.body_type        = $body_type,
                v.fuel_type        = $fuel_type,
                v.drive_type       = $drive_type,
                v.seating_capacity = $seating_capacity,
                v.category         = $category
            RETURN v.name AS name
            """,
            name=name,
            segment=props["segment"],
            body_type=props["body_type"],
            fuel_type=props["fuel_type"],
            drive_type=props["drive_type"],
            seating_capacity=props["seating_capacity"],
            category=props.get("category", "Passenger")
        )
        rows = result.data()
        if rows:
            updated += 1
        else:
            not_found.append(name)

    print(f"  → {updated} 件更新")
    if not_found:
        print(f"  マスタにあるが Neo4j に存在しないモデル ({len(not_found)} 件):")
        for n in not_found:
            print(f"    - {n}")

    # カバレッジ確認（SELECTED 上位30件）
    cov = session.run(
        """
        MATCH (c:Consumer)-[:SELECTED]->(v:VehicleModel)
        WITH v, count(c) AS cnt
        ORDER BY cnt DESC LIMIT 30
        RETURN v.name AS model, cnt, v.segment AS segment, v.body_type AS body_type
        """
    )
    print("\n  SELECTED 上位30 カバレッジ確認:")
    print(f"  {'モデル':<30} {'台数':>5}  {'segment':<20} {'body_type'}")
    covered = 0
    for r in cov.data():
        seg = r["segment"] or "（未設定）"
        bt  = r["body_type"] or "（未設定）"
        mark = "✓" if r["segment"] else "✗"
        if r["segment"]:
            covered += 1
        print(f"  {mark} {r['model']:<28} {r['cnt']:>5}  {seg:<20} {bt}")
    print(f"\n  上位30モデルのカバー率: {covered}/30")


def main():
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        step1a_update_decision_styles(session)
        step1b_update_vehicle_role(session)
        step1c_update_vehicle_models(session)
    driver.close()
    print("\n✅ Step 1a / 1b / 1c 完了")


if __name__ == "__main__":
    main()
