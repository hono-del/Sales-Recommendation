"""
Phase 5: Recommendation engine
Score = Need match 45% + Feature match 25% + Similar consumer 20% + EvalCriteria 10%
"""
import os
from dataclasses import dataclass, field
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

# UI の needs キー → v3 グラフ上の Need.name リスト
UI_TO_GRAPH_NEEDS: dict[str, list[str]] = {
    "safety":          ["DrivingConfidence", "AccidentAnxietyReduction", "EasyParking", "VisibilityConfidence"],
    "family":          ["FamilyComfort", "ChildSafety", "WeekendFamilyTrip", "StressFreeSchoolPickup"],
    "comfort":         ["FatigueReduction", "SmoothRideComfort", "RelaxingDrive", "QuietCabinExperience"],
    "space":           ["FlexibleCargoSpace", "FlatSeatUtility", "EasyLoading"],
    "fuel_efficiency": ["LowFuelAnxiety", "EfficientDailyMobility", "EnergyEfficiency"],
    "design":          ["PersonalExpression", "EmotionalAttachment", "PremiumFeeling"],
    "technology":      ["DrivingConfidence", "AccidentAnxietyReduction", "EasyParking"],
    "offroad":         ["OutdoorLifestyle", "AdventureLifestyle", "SnowDrivingConfidence"],
}

NEED_KEYWORDS: dict[str, list[str]] = {
    "safety": ["安全", "safety", "セーフティ", "衝突", "AEB", "ブレーキ"],
    "space": ["広", "空間", "ラゲッジ", "3列", "7人", "収納"],
    "fuel_efficiency": ["燃費", "ハイブリッド", "電気", "eco", "HV"],
    "comfort": ["快適", "乗り心地", "静粛"],
    "design": ["デザイン", "スタイル", "スポーティ"],
    "technology": ["先進", "ナビ", "システム", "テクノロジー", "Honda SENSING"],
    "family": ["ファミリー", "子ども", "チャイルド", "スライド", "後席"],
    "offroad": ["オフロード", "四駆", "AWD", "4WD", "雪道", "山道"],
}


@dataclass
class RecommendationRequest:
    family_size: int
    budget: int  # yen
    needs: list[str]
    usage: str = ""


@dataclass
class Recommendation:
    model: str
    score: float
    reason: str
    need_score: float = 0.0
    feature_score: float = 0.0
    consumer_score: float = 0.0
    ec_score: float = 0.0
    similar_consumers: list[str] = field(default_factory=list)


class RecommendationEngine:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def _expand_ui_needs(self, needs: list[str]) -> set[str]:
        """UI の needs キーを v3 Need.name の集合に展開する。"""
        expanded: set[str] = set()
        for need in needs:
            key = need.lower()
            for graph_need in UI_TO_GRAPH_NEEDS.get(key, []):
                expanded.add(graph_need.lower())
            expanded.add(key)
        return expanded

    def _get_all_vehicles(self) -> list[dict]:
        """製品データ（HAS_FEATURE → TechnicalFeature）が存在する車種のみ返す。"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (v:VehicleModel)
                WHERE (v)-[:HAS_FEATURE]->(:TechnicalFeature)
                RETURN v.name AS name,
                       v.category AS category,
                       v.price_range AS price_range,
                       v.fuel_type AS fuel_type,
                       v.seating_capacity AS seating
                """
            )
            return [dict(r) for r in result]

    def _vehicle_graph_needs(self, vehicle_name: str) -> set[str]:
        """v3: VehicleModel → TechnicalFeature → Capability → Need"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (v:VehicleModel {name: $vname})-[:HAS_FEATURE]->(:TechnicalFeature)
                      -[:REALIZES]->(:Capability)-[:SUPPORTS]->(n:Need)
                RETURN collect(DISTINCT n.name) AS needs
                """,
                vname=vehicle_name,
            )
            record = result.single()
        if not record:
            return set()
        return {n.lower() for n in (record["needs"] or []) if n}

    def _score_need_match(self, vehicle_name: str, needs: list[str]) -> float:
        """v3: Capability -[:SUPPORTS]-> Need 経由でニーズ適合度を算出。"""
        if not needs:
            return 0.0
        vehicle_needs = self._vehicle_graph_needs(vehicle_name)
        if not vehicle_needs:
            return 0.0
        matched_ui = 0
        for need in needs:
            graph_names = {n.lower() for n in UI_TO_GRAPH_NEEDS.get(need.lower(), [])}
            if graph_names & vehicle_needs:
                matched_ui += 1
        return min(matched_ui / len(needs), 1.0)

    def _score_feature_match(self, vehicle_name: str, needs: list[str]) -> float:
        """v3: TechnicalFeature のテキストと UI needs キーワードの一致。"""
        if not needs:
            return 0.0
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (v:VehicleModel {name: $vname})-[:HAS_FEATURE]->(tf:TechnicalFeature)
                RETURN tf.name AS feature
                """,
                vname=vehicle_name,
            )
            features_text = " ".join((r["feature"] or "").lower() for r in result)

        matched = 0
        for need in needs:
            keywords = NEED_KEYWORDS.get(need.lower(), [need.lower()])
            if any(kw in features_text for kw in keywords):
                matched += 1

        return min(matched / len(needs), 1.0)

    def _score_similar_consumers(
        self, vehicle_name: str, family_size: int, needs: list[str]
    ) -> tuple[float, list[str]]:
        """v3: Consumer -[:OWNED]-> VehicleOwnership -[:OF_MODEL]-> VehicleModel"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Consumer)-[own:OWNED]->(vo:VehicleOwnership {is_current: true})
                      -[:OF_MODEL]->(v:VehicleModel {name: $vname})
                RETURN c.id AS cid,
                       c.family_size AS fs,
                       vo.usage_pattern AS usage,
                       c.id AS title,
                       COALESCE(own.decision_weight, 1.0) AS weight
                LIMIT 200
                """,
                vname=vehicle_name,
            )
            selectors = [dict(r) for r in result]

        if not selectors:
            return 0.0, []

        target_needs = self._expand_ui_needs(needs)
        scores = []
        for sel in selectors:
            size_diff = abs((sel.get("fs") or 0) - family_size)
            size_sim = max(0, 1 - size_diff / 5)

            with self.driver.session() as session:
                need_result = session.run(
                    """
                    MATCH (c:Consumer {id: $cid})-[:HAS_NEED]->(n:Need)
                    RETURN n.name AS need
                    """,
                    cid=sel["cid"],
                )
                sel_needs = {(r["need"] or "").lower() for r in need_result}

            if target_needs:
                need_overlap = len(target_needs & sel_needs) / len(target_needs)
            else:
                need_overlap = 0.0

            sim = (size_sim * 0.4 + need_overlap * 0.6) * sel.get("weight", 1.0)
            scores.append((sim, sel.get("title") or sel.get("cid")))

        if not scores:
            return 0.0, []

        scores.sort(reverse=True)
        top_score = min(scores[0][0], 1.0)
        top_consumers = [s[1] for s in scores[:3]]
        return top_score, top_consumers

    def _score_eval_criteria_match(self, vehicle_name: str, needs: list[str]) -> float:
        """v3: Capability -[:INFLUENCES]-> EvaluationCriteria"""
        if not needs:
            return 0.0
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (v:VehicleModel {name: $vname})-[:HAS_FEATURE]->(:TechnicalFeature)
                      -[:REALIZES]->(:Capability)-[:INFLUENCES]->(ec:EvaluationCriteria)
                RETURN DISTINCT ec.name AS ec_name
                """,
                vname=vehicle_name,
            )
            ec_names = [(r["ec_name"] or "").lower() for r in result]

        if not ec_names:
            return 0.0

        matched = 0
        for need in needs:
            kws = NEED_KEYWORDS.get(need.lower(), [need.lower()])
            if any(any(kw in ec for kw in kws) for ec in ec_names):
                matched += 1

        return min(matched / len(needs), 1.0)

    def _parse_price_range(self, price_range: str) -> tuple[int, int]:
        """Extract min/max price in yen from price range string."""
        import re
        if not price_range:
            return 0, 99_999_999

        nums = re.findall(r"[\d,]+", price_range.replace("万円", "0000"))
        nums = [int(n.replace(",", "")) for n in nums]
        if len(nums) >= 2:
            return min(nums), max(nums)
        elif len(nums) == 1:
            return 0, nums[0]
        return 0, 99_999_999

    def recommend(self, req: RecommendationRequest, top_k: int = 3) -> list[Recommendation]:
        vehicles = self._get_all_vehicles()
        if not vehicles:
            return []

        scored = []
        for v in vehicles:
            # Budget filter
            _, max_price = self._parse_price_range(v.get("price_range") or "")
            if req.budget > 0 and max_price > 0 and max_price > req.budget * 1.2:
                continue  # way over budget, skip

            # Seating filter
            seating = v.get("seating") or 0
            if req.family_size > 0 and seating > 0 and seating < req.family_size:
                continue

            need_score = self._score_need_match(v["name"], req.needs)
            feat_score = self._score_feature_match(v["name"], req.needs)
            cons_score, similar = self._score_similar_consumers(v["name"], req.family_size, req.needs)

            # EvaluationCriteria bridge score (bonus)
            ec_score = self._score_eval_criteria_match(v["name"], req.needs)

            # Weights sum to 1.0: 0.45 + 0.25 + 0.20 + 0.10 = 1.00
            total = need_score * 0.45 + feat_score * 0.25 + cons_score * 0.2 + ec_score * 0.1

            reason_parts = []
            if need_score > 0.5:
                reason_parts.append(f"ニーズに{int(need_score*100)}%マッチ")
            if cons_score > 0.3:
                reason_parts.append(f"同様の家族構成の{len(similar)}名が選択")
            if ec_score > 0.3:
                reason_parts.append(f"評価基準とのマッチ{int(ec_score*100)}%")
            if not reason_parts:
                reason_parts.append("総合的な推薦")

            scored.append(Recommendation(
                model=v["name"],
                score=round(total, 3),
                reason="、".join(reason_parts),
                need_score=round(need_score, 3),
                feature_score=round(feat_score, 3),
                consumer_score=round(cons_score, 3),
                ec_score=round(ec_score, 3),
                similar_consumers=similar,
            ))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]


if __name__ == "__main__":
    engine = RecommendationEngine()
    try:
        test_cases = [
            RecommendationRequest(family_size=4, budget=15_000_000,
                                  needs=["safety", "space", "family"], usage="family_use"),
            RecommendationRequest(family_size=2, budget=8_000_000,
                                  needs=["fuel_efficiency", "technology", "design"], usage="commute"),
            RecommendationRequest(family_size=1, budget=20_000_000,
                                  needs=["comfort", "design", "technology"], usage="business"),
        ]
        for i, req in enumerate(test_cases, 1):
            print(f"\n[Test {i}] family={req.family_size}, budget={req.budget//10000}万円, "
                  f"needs={req.needs}")
            results = engine.recommend(req)
            for r in results:
                print(f"  {r.model:6s} score={r.score:.3f} "
                      f"(need={r.need_score:.2f} feat={r.feature_score:.2f} "
                      f"cons={r.consumer_score:.2f} ec={r.ec_score:.2f}) | {r.reason}")
    finally:
        engine.close()
