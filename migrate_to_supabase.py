"""
ローカルの sessions.json から Supabase にデータを移行するスクリプト
"""
import json
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

# ローカルの sessions.json を読み込み
SESSIONS_FILE = "data/demo/sessions.json"

def load_local_sessions():
    """ローカルの sessions.json を読み込む"""
    if not os.path.exists(SESSIONS_FILE):
        print(f"エラー: {SESSIONS_FILE} が見つかりません")
        return {}
    
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def filter_sessions_with_feedback(sessions, target_date=None):
    """フィードバックを持つセッションのみをフィルタ"""
    filtered = {}
    for session_id, session_data in sessions.items():
        feedbacks = session_data.get("service_feedbacks", [])
        if not feedbacks:
            continue
        
        # 日付フィルタ（指定がある場合）
        if target_date:
            created_at = session_data.get("created_at", "")
            if not created_at.startswith(target_date):
                continue
        
        filtered[session_id] = session_data
    
    return filtered

def upload_to_supabase(session_id, session_data):
    """単一セッションをSupabaseにアップロード"""
    url = f"{SUPABASE_URL}/rest/v1/demo_sessions"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    payload = {
        "session_id": session_id,
        "data": session_data,
        "created_at": session_data.get("created_at"),
        "updated_at": session_data.get("updated_at", datetime.utcnow().isoformat() + "Z")
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"  ❌ エラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  レスポンス: {e.response.text}")
        return False

def main():
    print("=" * 60)
    print("sessions.json → Supabase データ移行")
    print("=" * 60)
    print()
    
    # ローカルデータ読み込み
    print(f"[INFO] ローカルファイル読み込み: {SESSIONS_FILE}")
    all_sessions = load_local_sessions()
    print(f"   総セッション数: {len(all_sessions)}")
    print()
    
    # 6月5日のフィードバック付きセッションのみ抽出
    print("[INFO] 6月5日のフィードバック付きセッションを抽出中...")
    target_sessions = filter_sessions_with_feedback(all_sessions, target_date="2026-06-05")
    print(f"   対象セッション数: {len(target_sessions)}")
    print()
    
    if not target_sessions:
        print("[警告] 6月5日のフィードバックデータが見つかりませんでした")
        return
    
    # 移行確認
    print("以下のセッションを Supabase に移行します:")
    for i, (session_id, session_data) in enumerate(target_sessions.items(), 1):
        feedback_count = len(session_data.get("service_feedbacks", []))
        created_at = session_data.get("created_at", "不明")
        print(f"  {i}. {session_id[:20]}... (FB数: {feedback_count}, 作成: {created_at})")
    
    print()
    response = input("続行しますか？ (y/N): ")
    if response.lower() != 'y':
        print("中止しました")
        return
    
    # Supabaseにアップロード
    print()
    print("[INFO] Supabase にアップロード中...")
    success_count = 0
    fail_count = 0
    
    for i, (session_id, session_data) in enumerate(target_sessions.items(), 1):
        print(f"  [{i}/{len(target_sessions)}] {session_id[:30]}...", end=" ")
        if upload_to_supabase(session_id, session_data):
            print("OK")
            success_count += 1
        else:
            print("FAIL")
            fail_count += 1
    
    print()
    print("=" * 60)
    print(f"[結果] 成功: {success_count} / 失敗: {fail_count}")
    print("=" * 60)
    print()
    print("確認URL: https://sales-recommendation.vercel.app/demo/feedback-logs")
    print()

if __name__ == "__main__":
    main()
