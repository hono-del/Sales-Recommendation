"""
Phase 5: Recommendation engine
Score = Need match 45% + Feature match 25% + Similar consumer 20% + EvalCriteria 10%
+ Load Boost (0-20 pts per detected load)
"""
import os
import json
from pathlib import Path
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
    budget: int  # yen (deprecated: use budget_min/budget_max)
    needs: list[str]
    usage: str = ""
    detected_loads: list[str] = field(default_factory=list)  # Load 検出結果
    budget_min: int = 0  # 予算下限（円）
    budget_max: int = 0  # 予算上限（円）


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
    load_boost: float = 0.0  # Load によるブーストスコア
    matched_load_features: list[str] = field(default_factory=list)  # マッチした Load 対応機能


class RecommendationEngine:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            connection_timeout=5.0,
            connection_acquisition_timeout=5.0,
        )
        
        # Load マッピング設定を読み込み
        config_path = Path(__file__).parent.parent / "config" / "load-feature-mapping.json"
        if config_path.exists():
            self.load_mapping = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            self.load_mapping = {"load_to_features": {}}

    def close(self):
        self.driver.close()

    def _expand_ui_needs(self, needs: list[str]) -> set[str]:
        """UI needs キーまたは KG Need.name を v3 Need.name 集合に展開する。"""
        expanded: set[str] = set()
        for need in needs:
            key = need.lower()
            mapped = UI_TO_GRAPH_NEEDS.get(key, [])
            if mapped:
                for graph_need in mapped:
                    expanded.add(graph_need.lower())
            else:
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
            if not graph_names:
                graph_names = {need.lower()}
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
    
    def _get_vehicle_features(self, vehicle_name: str) -> list[str]:
        """車種の TechnicalFeature リストを取得"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (v:VehicleModel {name: $vname})-[:HAS_FEATURE]->(tf:TechnicalFeature)
                RETURN collect(tf.name) AS features
                """,
                vname=vehicle_name
            )
            record = result.single()
            return record["features"] if record else []
    
    def _calculate_load_boost(
        self, 
        vehicle_name: str, 
        detected_loads: list[str]
    ) -> tuple[float, list[str]]:
        """
        車種が持つ Load 対応機能のブーストスコアを計算
        
        Args:
            vehicle_name: 車種名
            detected_loads: 検出された Load ラベルのリスト (e.g., ["parking", "fatigue"])
        
        Returns:
            (boost_score, matched_features): ブーストポイント（正規化前）とマッチした機能リスト
        """
        if not detected_loads:
            return 0.0, []
        
        # 車種の全機能を取得
        vehicle_features = self._get_vehicle_features(vehicle_name)
        if not vehicle_features:
            return 0.0, []
        
        total_boost = 0.0
        matched_features = []
        load_feature_matches = {}  # Load ごとに1回だけブースト
        
        for load_key in detected_loads:
            load_config = self.load_mapping["load_to_features"].get(load_key, {})
            boost = load_config.get("boost_score", 0)
            target_features = load_config.get("features", [])
            
            # 部分一致で機能をチェック（1つの Load につき1回だけブースト）
            for target in target_features:
                for vehicle_feature in vehicle_features:
                    if target in vehicle_feature or vehicle_feature in target:
                        if load_key not in load_feature_matches:
                            total_boost += boost
                            load_feature_matches[load_key] = vehicle_feature
                            matched_features.append(f"{vehicle_feature}({load_key})")
                        break
                if load_key in load_feature_matches:
                    break
        
        # ブーストスコアを 0-20 の範囲に正規化
        normalized_boost = min(total_boost / 100.0, 0.20)
        
        return normalized_boost, matched_features
    
    def _generate_load_reason(
        self, 
        detected_loads: list[str], 
        matched_features: list[str]
    ) -> list[str]:
        """
        Load に基づく推薦理由を生成
        
        Args:
            detected_loads: 検出された Load ラベル
            matched_features: マッチした機能リスト（"機能名(load_key)" 形式）
        
        Returns:
            推薦理由のリスト
        """
        load_labels = self.load_mapping.get("load_labels_ja", {})
        reasons = []
        
        # matched_features から load_key を抽出
        load_feature_map = {}
        for feature_str in matched_features:
            if "(" in feature_str and ")" in feature_str:
                feature_name = feature_str.split("(")[0]
                load_key = feature_str.split("(")[1].rstrip(")")
                if load_key not in load_feature_map:
                    load_feature_map[load_key] = []
                load_feature_map[load_key].append(feature_name)
        
        # Load ごとに推薦理由を生成
        for load_key in detected_loads:
            if load_key not in load_feature_map:
                continue
            
            features = load_feature_map[load_key]
            load_label = load_labels.get(load_key, load_key)
            
            if load_key == "parking":
                reasons.append(f"{features[0]}で駐車・狭い道の不安を解消")
            elif load_key == "fatigue":
                reasons.append(f"{features[0]}で長距離運転の疲労を軽減")
            elif load_key == "maintenance":
                reasons.append(f"{features[0]}で維持費を抑えられる")
            elif load_key == "family_dissatisfaction":
                reasons.append(f"{features[0]}で家族全員が快適に移動")
            elif load_key == "traffic":
                reasons.append(f"{features[0]}で渋滞時のストレスを軽減")
            elif load_key == "difficult_operation":
                reasons.append(f"{features[0]}で操作をサポート")
            elif load_key == "too_much_info":
                reasons.append(f"{features[0]}で情報整理をアシスト")
            else:
                reasons.append(f"{features[0]}で{load_label}に対応")
        
        return reasons[:2]  # 最大2つまで

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
        
        # 予算範囲を決定（budget_min/budget_max が指定されていればそちらを優先）
        budget_min = req.budget_min if req.budget_min > 0 else req.budget
        budget_max = req.budget_max if req.budget_max > 0 else req.budget * 1.2
        
        for v in vehicles:
            # Budget filter（範囲ベース）
            min_price, max_price = self._parse_price_range(v.get("price_range") or "")
            if budget_min > 0 and max_price > 0:
                # 車種の最低価格が予算上限の120%を超える場合はスキップ
                if min_price > budget_max * 1.2:
                    continue
                # 車種の最高価格が予算下限の80%未満の場合はスキップ
                if max_price < budget_min * 0.8:
                    continue

            # Seating filter
            seating = v.get("seating") or 0
            if req.family_size > 0 and seating > 0 and seating < req.family_size:
                continue

            need_score = self._score_need_match(v["name"], req.needs)
            feat_score = self._score_feature_match(v["name"], req.needs)
            cons_score, similar = self._score_similar_consumers(v["name"], req.family_size, req.needs)

            # EvaluationCriteria bridge score (bonus)
            ec_score = self._score_eval_criteria_match(v["name"], req.needs)

            # Load Boost スコア計算
            load_boost, matched_load_features = self._calculate_load_boost(
                v["name"], 
                req.detected_loads
            )

            # Base score: 既存のスコア (0-1.0)
            base_score = need_score * 0.45 + feat_score * 0.25 + cons_score * 0.2 + ec_score * 0.1
            
            # Final score: base_score + load_boost (最大 1.20、表示時は 100 を上限とする)
            total = base_score + load_boost

            reason_parts = []
            if need_score > 0.5:
                reason_parts.append(f"ニーズに{int(need_score*100)}%マッチ")
            if cons_score > 0.3:
                reason_parts.append(f"同様の家族構成の{len(similar)}名が選択")
            if ec_score > 0.3:
                reason_parts.append(f"評価基準とのマッチ{int(ec_score*100)}%")
            
            # Load Boost による推薦理由を追加
            if load_boost > 0 and matched_load_features:
                load_reasons = self._generate_load_reason(req.detected_loads, matched_load_features)
                if load_reasons:
                    reason_parts.extend(load_reasons)
            
            if not reason_parts:
                reason_parts.append("総合的な推薦")

            scored.append(Recommendation(
                model=v["name"],
                score=round(min(total, 1.0), 3),  # 表示は 0-1.0 に正規化
                reason="、".join(reason_parts),
                need_score=round(need_score, 3),
                feature_score=round(feat_score, 3),
                consumer_score=round(cons_score, 3),
                ec_score=round(ec_score, 3),
                similar_consumers=similar,
                load_boost=round(load_boost, 3),
                matched_load_features=matched_load_features,
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
