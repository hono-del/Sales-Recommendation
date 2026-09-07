"""
Supabaseに保存されているデータを確認するスクリプト
"""
import os
import requests
from datetime import datetime

# Supabase接続情報
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("エラー: 環境変数 SUPABASE_URL と SUPABASE_SERVICE_KEY を設定してください")
    print("\nPowerShell で設定する場合:")
    print('$env:SUPABASE_URL="https://vgkojkjsqfpphywcahqk.supabase.co"')
    print('$env:SUPABASE_SERVICE_KEY="your-service-role-key"')
    exit(1)

def check_supabase_data():
    """Supabaseのデータを確認"""
    url = f"{SUPABASE_URL}/rest/v1/demo_sessions"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    
    params = {
        "select": "session_id,created_at,updated_at,data",
        "order": "updated_at.desc"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        sessions = response.json()
        
        print("=" * 60)
        print("Supabase データ確認")
        print("=" * 60)
        print()
        print(f"総セッション数: {len(sessions)}")
        print()
        
        if not sessions:
            print("データがありません")
            return
        
        print("セッション一覧（更新日時順）:")
        print()
        
        for i, session in enumerate(sessions, 1):
            session_id = session.get("session_id", "不明")
            created_at = session.get("created_at", "不明")
            updated_at = session.get("updated_at", "不明")
            data = session.get("data", {})
            
            # フィードバック数を取得
            feedbacks = data.get("service_feedbacks", [])
            feedback_count = len(feedbacks)
            
            print(f"[{i}] Session ID: {session_id[:40]}...")
            print(f"    作成日時: {created_at}")
            print(f"    更新日時: {updated_at}")
            print(f"    フィードバック数: {feedback_count}")
            
            if feedbacks:
                print(f"    フィードバック内容:")
                for fb in feedbacks[:3]:  # 最初の3件を表示
                    service_id = fb.get("service_id", "不明")
                    feedback_value = fb.get("feedback_value", "不明")
                    print(f"      - {service_id}: {feedback_value}")
                if len(feedbacks) > 3:
                    print(f"      ... 他 {len(feedbacks) - 3} 件")
            print()
        
        print("=" * 60)
        
    except requests.exceptions.RequestException as e:
        print(f"エラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"レスポンス: {e.response.text}")

if __name__ == "__main__":
    check_supabase_data()
