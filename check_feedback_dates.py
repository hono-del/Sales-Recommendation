"""
sessions.json に含まれるフィードバックデータの日付を確認するスクリプト
"""
import json
import os
from collections import defaultdict

SESSIONS_FILE = "data/demo/sessions.json"

def main():
    print("=" * 60)
    print("フィードバックデータの日付確認")
    print("=" * 60)
    print()
    
    if not os.path.exists(SESSIONS_FILE):
        print(f"エラー: {SESSIONS_FILE} が見つかりません")
        return
    
    print(f"[INFO] ファイル読み込み中: {SESSIONS_FILE}")
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        all_sessions = json.load(f)
    
    print(f"   総セッション数: {len(all_sessions)}")
    print()
    
    # フィードバック付きセッションを日付別に集計
    feedback_by_date = defaultdict(list)
    
    for session_id, session_data in all_sessions.items():
        feedbacks = session_data.get("service_feedbacks", [])
        if not feedbacks:
            continue
        
        created_at = session_data.get("created_at", "不明")
        updated_at = session_data.get("updated_at", "不明")
        
        # 日付部分を抽出（YYYY-MM-DD）
        date_key = created_at[:10] if len(created_at) >= 10 else created_at
        
        feedback_by_date[date_key].append({
            "session_id": session_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "feedback_count": len(feedbacks),
            "feedbacks": feedbacks
        })
    
    print("[結果] フィードバック付きセッションの日付別集計:")
    print()
    
    if not feedback_by_date:
        print("[警告] フィードバックデータが見つかりませんでした")
        return
    
    # 日付でソート
    sorted_dates = sorted(feedback_by_date.keys(), reverse=True)
    
    for date in sorted_dates:
        sessions = feedback_by_date[date]
        total_feedbacks = sum(s["feedback_count"] for s in sessions)
        print(f"[日付] {date}")
        print(f"   セッション数: {len(sessions)}")
        print(f"   総フィードバック数: {total_feedbacks}")
        
        # 最初の数件の詳細を表示
        for i, session in enumerate(sessions[:3], 1):
            print(f"   {i}. Session ID: {session['session_id'][:30]}...")
            print(f"      作成: {session['created_at']}")
            print(f"      更新: {session['updated_at']}")
            print(f"      FB数: {session['feedback_count']}")
            # フィードバックの内容を簡易表示
            for fb in session['feedbacks'][:2]:
                service_id = fb.get('service_id', '不明')
                feedback_value = fb.get('feedback_value', '不明')
                print(f"        - {service_id}: {feedback_value}")
        
        if len(sessions) > 3:
            print(f"   ... 他 {len(sessions) - 3} セッション")
        
        print()
    
    print("=" * 60)

if __name__ == "__main__":
    main()
