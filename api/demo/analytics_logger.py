"""
分析用ログ収集モジュール
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class AnalyticsLogger:
    """セッションデータを分析用ログとして保存"""
    
    def __init__(self, log_dir: Path | None = None):
        if log_dir is None:
            log_dir = Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "logs"
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_session_analytics(self, session: dict[str, Any]) -> dict[str, Any]:
        """
        セッションの分析データをログ出力
        
        Args:
            session: セッションデータ
        
        Returns:
            ログエントリ
        """
        session_id = session.get("session_id", "unknown")
        
        # プロファイルデータ抽出
        profile_data = session.get("profile", {})
        profile_scores = profile_data.get("profile", {}) if isinstance(profile_data, dict) else {}
        
        # 価値観プロファイル
        value_profile = {
            "safety": profile_scores.get("score_safety", 0),
            "family": profile_scores.get("score_family", 0),
            "efficiency": profile_scores.get("score_efficiency", 0),
            "enjoyment": profile_scores.get("score_enjoyment", 0),
            "adventure": profile_scores.get("score_adventure", 0),
        }
        
        # ニーズ抽出
        mapped_needs = profile_data.get("mapped_needs", []) if isinstance(profile_data, dict) else []
        
        # 懸念事項（Load）抽出
        detected_loads = []
        if isinstance(profile_data, dict):
            loads_data = profile_data.get("detected_loads", [])
            if isinstance(loads_data, list):
                detected_loads = [
                    {
                        "name": load.get("name", ""),
                        "description": load.get("description", ""),
                        "related_values": load.get("related_values", []),
                    }
                    for load in loads_data
                ]
        
        # サービス推薦結果（キャッシュから取得）
        recommended_services = []
        cached_recs = session.get("cached_service_recommendations", {})
        if isinstance(cached_recs, dict):
            services = cached_recs.get("services", [])
            if isinstance(services, list):
                recommended_services = [
                    {
                        "service_id": svc.get("service_id", svc.get("id", "")),
                        "title": svc.get("title", ""),
                        "rank": idx + 1,
                        "score": svc.get("score", 0),
                        "matched_needs": svc.get("matched_needs", []),
                        "matched_loads": svc.get("matched_loads", []),
                    }
                    for idx, svc in enumerate(services[:10])  # 上位10件まで
                ]
        
        # フィードバックデータ
        feedbacks = session.get("service_feedbacks", [])
        service_feedbacks = []
        if isinstance(feedbacks, list):
            service_feedbacks = [
                {
                    "service_id": fb.get("service_id", ""),
                    "service_rank": fb.get("service_rank"),
                    "feedback_value": fb.get("feedback_value", ""),
                    "timestamp": fb.get("timestamp", ""),
                }
                for fb in feedbacks
            ]
        
        # ログエントリ作成
        log_entry = {
            "session_id": session_id,
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "created_at": session.get("created_at", ""),
            "status": session.get("status", ""),
            "value_profile": value_profile,
            "mapped_needs": mapped_needs,
            "detected_loads": detected_loads,
            "recommended_services": recommended_services,
            "service_feedbacks": service_feedbacks,
            "answers_count": len(session.get("answers", [])),
        }
        
        # ログファイルに保存（JSON Lines形式）
        log_file = self.log_dir / "session_analytics.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        return log_entry
    
    def get_all_logs(self) -> list[dict[str, Any]]:
        """
        全ログを取得
        
        Returns:
            ログエントリのリスト
        """
        log_file = self.log_dir / "session_analytics.jsonl"
        if not log_file.exists():
            return []
        
        logs = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return logs
    
    def find_similar_profiles(self, current_profile: dict[str, float], threshold: float = 30.0) -> dict[str, Any]:
        """
        現在のプロファイルと類似した過去のプロファイルを検索
        
        Args:
            current_profile: 現在の価値観プロファイル（safety, family, efficiency, enjoyment, adventure）
            threshold: 類似と判定する距離の閾値（デフォルト30.0）
        
        Returns:
            {
                "total_users": int,  # 総ユーザー数（ユニークセッション数）
                "similar_users": int,  # 類似ユーザー数
                "similarity_rate": float  # 類似率（％）
            }
        """
        logs = self.get_all_logs()
        
        # ユニークなセッションIDのセット
        unique_sessions = set()
        similar_sessions = set()
        
        for log in logs:
            session_id = log.get("session_id", "")
            if not session_id:
                continue
            
            unique_sessions.add(session_id)
            
            # 価値観プロファイル取得
            log_profile = log.get("value_profile", {})
            
            # ユークリッド距離を計算
            distance = self._calculate_profile_distance(current_profile, log_profile)
            
            # 閾値以下なら類似とみなす
            if distance <= threshold:
                similar_sessions.add(session_id)
        
        total_users = len(unique_sessions)
        similar_users = len(similar_sessions)
        similarity_rate = (similar_users / total_users * 100) if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "similar_users": similar_users,
            "similarity_rate": round(similarity_rate, 1),
        }
    
    def _calculate_profile_distance(self, profile1: dict[str, float], profile2: dict[str, float]) -> float:
        """
        2つの価値観プロファイル間のユークリッド距離を計算
        
        Args:
            profile1: プロファイル1
            profile2: プロファイル2
        
        Returns:
            ユークリッド距離
        """
        axes = ["safety", "family", "efficiency", "enjoyment", "adventure"]
        
        distance_squared = 0.0
        for axis in axes:
            val1 = profile1.get(axis, 0)
            val2 = profile2.get(axis, 0)
            distance_squared += (val1 - val2) ** 2
        
        return distance_squared ** 0.5
    
    def get_feedback_stats_for_profile(
        self, 
        current_profile: dict[str, float], 
        threshold: float = 30.0
    ) -> dict[str, dict[str, Any]]:
        """
        類似プロファイルのフィードバック統計を取得
        
        Args:
            current_profile: 現在の価値観プロファイル
            threshold: 類似と判定する距離の閾値
        
        Returns:
            {
                "S-1": {
                    "total_feedbacks": 10,
                    "positive_count": 6,  # somewhat_interested + want_details
                    "negative_count": 4,  # not_fit + low_interest
                    "positive_rate": 0.6,
                    "negative_rate": 0.4,
                    "net_sentiment": 0.2  # positive_rate - negative_rate
                },
                ...
            }
        """
        logs = self.get_all_logs()
        
        # 類似プロファイルのフィードバックを収集
        service_feedbacks: dict[str, list[str]] = {}
        
        for log in logs:
            # 価値観プロファイル取得
            log_profile = log.get("value_profile", {})
            
            # ユークリッド距離を計算
            distance = self._calculate_profile_distance(current_profile, log_profile)
            
            # 閾値以下なら類似とみなす
            if distance <= threshold:
                # フィードバックデータ取得
                feedbacks = log.get("service_feedbacks", [])
                for fb in feedbacks:
                    service_id = fb.get("service_id", "")
                    feedback_value = fb.get("feedback_value", "")
                    
                    if service_id and feedback_value:
                        if service_id not in service_feedbacks:
                            service_feedbacks[service_id] = []
                        service_feedbacks[service_id].append(feedback_value)
        
        # 統計計算
        stats: dict[str, dict[str, Any]] = {}
        for service_id, feedbacks in service_feedbacks.items():
            total = len(feedbacks)
            positive = sum(1 for fb in feedbacks if fb in ["somewhat_interested", "want_details"])
            negative = sum(1 for fb in feedbacks if fb in ["not_fit", "low_interest"])
            
            positive_rate = positive / total if total > 0 else 0
            negative_rate = negative / total if total > 0 else 0
            net_sentiment = positive_rate - negative_rate
            
            stats[service_id] = {
                "total_feedbacks": total,
                "positive_count": positive,
                "negative_count": negative,
                "positive_rate": round(positive_rate, 3),
                "negative_rate": round(negative_rate, 3),
                "net_sentiment": round(net_sentiment, 3),
            }
        
        return stats
    
    def export_to_csv(self, output_path: Path | None = None) -> Path:
        """
        ログをCSV形式でエクスポート
        
        Args:
            output_path: 出力先パス（省略時は logs/analytics.csv）
        
        Returns:
            出力ファイルパス
        """
        import csv
        
        if output_path is None:
            output_path = self.log_dir / "analytics.csv"
        
        logs = self.get_all_logs()
        
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            if not logs:
                return output_path
            
            # ヘッダー作成
            fieldnames = [
                "session_id",
                "logged_at",
                "created_at",
                "status",
                "value_safety",
                "value_family",
                "value_efficiency",
                "value_enjoyment",
                "value_adventure",
                "needs_count",
                "needs_list",
                "loads_count",
                "loads_list",
                "services_count",
                "services_list",
                "feedbacks_count",
                "feedback_positive_count",
                "feedback_negative_count",
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in logs:
                value_profile = log.get("value_profile", {})
                needs = log.get("mapped_needs", [])
                loads = log.get("detected_loads", [])
                services = log.get("recommended_services", [])
                feedbacks = log.get("service_feedbacks", [])
                
                # フィードバック集計
                positive_feedback = sum(
                    1 for fb in feedbacks 
                    if fb.get("feedback_value") in ["somewhat_interested", "want_details"]
                )
                negative_feedback = sum(
                    1 for fb in feedbacks 
                    if fb.get("feedback_value") in ["not_fit", "low_interest"]
                )
                
                row = {
                    "session_id": log.get("session_id", ""),
                    "logged_at": log.get("logged_at", ""),
                    "created_at": log.get("created_at", ""),
                    "status": log.get("status", ""),
                    "value_safety": value_profile.get("safety", 0),
                    "value_family": value_profile.get("family", 0),
                    "value_efficiency": value_profile.get("efficiency", 0),
                    "value_enjoyment": value_profile.get("enjoyment", 0),
                    "value_adventure": value_profile.get("adventure", 0),
                    "needs_count": len(needs),
                    "needs_list": ", ".join(needs[:5]),  # 上位5件
                    "loads_count": len(loads),
                    "loads_list": ", ".join([ld.get("name", "") for ld in loads]),
                    "services_count": len(services),
                    "services_list": ", ".join([svc.get("title", "") for svc in services[:5]]),
                    "feedbacks_count": len(feedbacks),
                    "feedback_positive_count": positive_feedback,
                    "feedback_negative_count": negative_feedback,
                }
                writer.writerow(row)
        
        return output_path


_logger: Optional[AnalyticsLogger] = None


def get_analytics_logger() -> AnalyticsLogger:
    """グローバルロガーインスタンスを取得"""
    global _logger
    if _logger is None:
        _logger = AnalyticsLogger()
    return _logger
