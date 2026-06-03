"""
Service Offering Recommendation Engine

ユーザーのプロファイル（Need, Load、価値観）に基づいて
アップグレード・ダウングレードサービスを推薦する
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


@dataclass
class ServiceRecommendationRequest:
    """サービス推薦リクエスト"""
    needs: list[str] = field(default_factory=list)  # ユーザーのNeeds（KG Need names）
    detected_loads: list[str] = field(default_factory=list)  # 検出されたLoad
    profile_scores: dict[str, float] = field(default_factory=dict)  # 価値観スコア
    lifecycle_stage: str = "ownership"  # ライフサイクルステージ
    direction_preference: Optional[str] = None  # upgrade/downgrade/None（全て）


@dataclass
class ServiceRecommendation:
    """推薦されたサービス"""
    service_id: str
    title: str
    one_liner: str
    direction: str
    domain: str
    score: float
    matched_needs: list[str] = field(default_factory=list)
    matched_loads: list[str] = field(default_factory=list)
    value_alignment: float = 0.0
    pitch: str = ""
    need_rationale: str = ""
    # 個別スコア（v2.1追加）
    need_score: float = 0.0
    load_score: float = 0.0
    value_score: float = 0.0


class ServiceRecommendationEngine:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            connection_timeout=5.0,
            connection_acquisition_timeout=5.0,
        )
    
    def close(self):
        self.driver.close()
    
    def _fetch_all_services(self) -> list[dict]:
        """全サービスを取得（公開メソッド）"""
        return self._get_all_services()
    
    def recommend(
        self,
        req: ServiceRecommendationRequest,
        top_k: int = 5
    ) -> list[ServiceRecommendation]:
        """サービスを推薦"""
        services = self._get_all_services()
        if not services:
            return []
        
        scored = []
        for service in services:
            # Direction フィルター
            if req.direction_preference and service['direction'] != req.direction_preference:
                continue
            
            # Lifecycle フィルター（緩い）
            if service['lifecycle'] and service['lifecycle'] != req.lifecycle_stage:
                # ownership サービスは全員に推薦可能
                if service['lifecycle'] != 'ownership':
                    continue
            
            # スコアリング
            need_score, matched_needs = self._score_need_match(
                service['id'], req.needs
            )
            load_score, matched_loads = self._score_load_match(
                service['id'], req.detected_loads
            )
            value_score = self._score_value_alignment(
                service['id'], req.profile_scores
            )
            
            # 総合スコア
            # Need match: 40%, Load match: 40%, Value alignment: 20%
            total_score = (
                need_score * 0.4 +
                load_score * 0.4 +
                value_score * 0.2
            )
            
            if total_score < 0.1:  # 最低閾値
                continue
            
            scored.append(ServiceRecommendation(
                service_id=service['id'],
                title=service['title'],
                one_liner=service['one_liner'],
                direction=service['direction'],
                domain=service['domain'],
                score=total_score,
                matched_needs=matched_needs,
                matched_loads=matched_loads,
                value_alignment=value_score,
                pitch=service['pitch_template'],
                need_rationale=service['need_rationale'],
                # 個別スコア
                need_score=need_score,
                load_score=load_score,
                value_score=value_score,
            ))
        
        # スコアでソート
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]
    
    def _get_all_services(self) -> list[dict]:
        """全ServiceOfferingを取得（Neo4j or JSON fallback）"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:ServiceOffering)
                    RETURN s.id AS id,
                           s.title AS title,
                           s.one_liner AS one_liner,
                           s.direction AS direction,
                           s.domain AS domain,
                           s.lifecycle AS lifecycle,
                           s.pitch_template AS pitch_template,
                           s.need_rationale AS need_rationale,
                           s.load_labels AS load_labels,
                           s.value_axes AS value_axes
                """)
                services = [dict(r) for r in result]
                if services:
                    return services
        except Exception as e:
            print(f"[ServiceRecommendation] Neo4j unavailable, using JSON fallback: {e}")
        
        # Fallback: JSONファイルから読み込む
        try:
            json_path = Path(__file__).resolve().parent.parent / "config" / "service-offerings.json"
            data = json.loads(json_path.read_text(encoding="utf-8"))
            offerings = data.get("offerings", [])
            
            # Neo4jと同じ形式に変換
            services = []
            for offer in offerings:
                # status チェックを緩和（draft も含める）
                status = offer.get("status", "draft")
                if status not in ["active", "draft"]:
                    continue
                services.append({
                    "id": offer["id"],
                    "title": offer["title"],
                    "one_liner": offer["one_liner"],
                    "direction": offer["direction"],
                    "domain": offer["domain"],
                    "lifecycle": offer.get("lifecycle", "ownership"),
                    "pitch_template": (offer.get("analog") or {}).get("pitch_template", ""),
                    "need_rationale": offer.get("need_rationale", ""),
                    "load_labels": offer.get("load_labels", []),
                    "value_axes": offer.get("value_axes", []),
                    "primary_needs": [n["name"] for n in offer.get("primary_needs", [])],
                    "secondary_needs": [n["name"] for n in offer.get("secondary_needs", [])]
                })
            print(f"[ServiceRecommendation] Loaded {len(services)} services from JSON")
            return services
        except Exception as json_e:
            print(f"[ServiceRecommendation] JSON fallback failed: {json_e}")
            return []
    
    def _score_need_match(
        self,
        service_id: str,
        user_needs: list[str]
    ) -> tuple[float, list[str]]:
        """Needマッチスコア（Neo4j or JSON fallback）"""
        if not user_needs:
            return 0.0, []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:ServiceOffering {id: $service_id})-[r:ADDRESSES]->(n:Need)
                    WHERE n.name IN $user_needs
                    RETURN n.name AS need, n.label AS label, r.priority AS priority
                    ORDER BY r.priority
                """, service_id=service_id, user_needs=user_needs)
                
                matches = [dict(r) for r in result]
            
            if matches:
                # Priority加重スコア（primary=1.0, secondary=0.5）
                weighted_score = 0.0
                for match in matches:
                    priority = match['priority']
                    weight = 1.0 if priority <= 3 else 0.5
                    weighted_score += weight
                
                # 正規化（最大=ユーザーNeeds数）
                score = min(weighted_score / len(user_needs), 1.0)
                matched_need_names = [m['need'] for m in matches]
                
                return score, matched_need_names
        except Exception:
            pass
        
        # Fallback: JSONデータから計算
        services = self._get_all_services()
        service_data = next((s for s in services if s['id'] == service_id), None)
        if not service_data:
            return 0.0, []
        
        primary_needs = service_data.get('primary_needs', [])
        secondary_needs = service_data.get('secondary_needs', [])
        
        # マッチしたNeed
        matched_primary = [n for n in user_needs if n in primary_needs]
        matched_secondary = [n for n in user_needs if n in secondary_needs]
        
        if not matched_primary and not matched_secondary:
            return 0.0, []
        
        # Priority加重スコア
        weighted_score = len(matched_primary) * 1.0 + len(matched_secondary) * 0.5
        score = min(weighted_score / len(user_needs), 1.0)
        matched_need_names = matched_primary + matched_secondary
        
        return score, matched_need_names
    
    def _score_load_match(
        self,
        service_id: str,
        detected_loads: list[str]
    ) -> tuple[float, list[str]]:
        """Load マッチスコア（Neo4j or JSON fallback）"""
        if not detected_loads:
            return 0.0, []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:ServiceOffering {id: $service_id})
                    WHERE s.load_labels IS NOT NULL
                    RETURN s.load_labels AS service_loads
                """, service_id=service_id)
                
                record = result.single()
            
            if record and record['service_loads']:
                service_loads = record['service_loads']
                matched = [load for load in detected_loads if load in service_loads]
                
                if matched:
                    score = len(matched) / len(detected_loads)
                    return score, matched
        except Exception:
            pass
        
        # Fallback: JSONデータから計算
        services = self._get_all_services()
        service_data = next((s for s in services if s['id'] == service_id), None)
        if not service_data:
            return 0.0, []
        
        service_loads = service_data.get('load_labels', [])
        if not service_loads:
            return 0.0, []
        
        matched = [load for load in detected_loads if load in service_loads]
        
        if not matched:
            return 0.0, []
        
        # スコア = マッチ数 / ユーザーのLoad数
        score = len(matched) / len(detected_loads)
        return score, matched
    
    def _score_value_alignment(
        self,
        service_id: str,
        profile_scores: dict[str, float]
    ) -> float:
        """価値観軸のアライメントスコア（Neo4j or JSON fallback）"""
        if not profile_scores:
            return 0.0
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:ServiceOffering {id: $service_id})
                    WHERE s.value_axes IS NOT NULL
                    RETURN s.value_axes AS value_axes
                """, service_id=service_id)
                
                record = result.single()
            
            if record and record['value_axes']:
                value_axes = record['value_axes']
                if value_axes:
                    axis_scores = [profile_scores.get(axis, 0.0) for axis in value_axes]
                    return sum(axis_scores) / len(axis_scores) if axis_scores else 0.0
        except Exception:
            pass
        
        # Fallback: JSONデータから計算
        services = self._get_all_services()
        service_data = next((s for s in services if s['id'] == service_id), None)
        if not service_data:
            return 0.0
        
        value_axes = service_data.get('value_axes', [])
        if not value_axes:
            return 0.0
        
        # 各軸のスコアの平均
        axis_scores = [profile_scores.get(axis, 0.0) for axis in value_axes]
        return sum(axis_scores) / len(axis_scores) if axis_scores else 0.0


def recommend_services_for_session(
    session: dict,
    top_k: int = 5
) -> list[dict]:
    """セッションから直接サービス推薦を生成"""
    profile_data = session.get("profile") or {}
    
    # Needs
    needs = profile_data.get("mapped_needs") or []
    
    # Loads（詳細情報から名前だけを抽出）
    detected_load_details = profile_data.get("detected_loads") or []
    detected_loads = [load["name"] if isinstance(load, dict) else load for load in detected_load_details]
    
    # Profile scores（0-100 → 0-1 に正規化）
    prof = profile_data.get("profile") or {}
    profile_scores = {
        "safety": float(prof.get("score_safety", 0)) / 100.0,
        "family": float(prof.get("score_family", 0)) / 100.0,
        "efficiency": float(prof.get("score_efficiency", 0)) / 100.0,
        "enjoyment": float(prof.get("score_enjoyment", 0)) / 100.0,
        "adventure": float(prof.get("score_adventure", 0)) / 100.0,
    }
    
    # Lifecycle（デフォルト: ownership）
    lifecycle = session.get("lifecycle_stage", "ownership")
    
    try:
        engine = ServiceRecommendationEngine()
        try:
            req = ServiceRecommendationRequest(
                needs=needs,
                detected_loads=detected_loads,
                profile_scores=profile_scores,
                lifecycle_stage=lifecycle,
            )
            
            results = engine.recommend(req, top_k=top_k)
            
            # 辞書形式に変換
            services = []
            for r in results:
                services.append({
                    "id": r.service_id,
                    "title": r.title,
                    "one_liner": r.one_liner,
                    "direction": r.direction,
                    "domain": r.domain,
                    "score": round(r.score, 3),
                    "matched_needs": r.matched_needs[:5],  # 上位5件
                    "matched_loads": r.matched_loads,
                    "value_alignment": round(r.value_alignment, 3),
                    "pitch": r.pitch,
                    "need_rationale": r.need_rationale,
                    # 個別スコア（v2.1追加）
                    "need_score": round(r.need_score, 3),
                    "load_score": round(r.load_score, 3),
                    "value_score": round(r.value_score, 3),
                })
            
            return services
        
        finally:
            engine.close()
    
    except Exception as e:
        # Fallback: 空リスト
        print(f"[ServiceRecommendation] Error: {e}")
        return []
