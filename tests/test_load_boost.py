"""
Load Boost 機能のテスト

テストケース:
1. 駐車不安のあるファミリー層 → パノラミックビューモニター搭載車がブースト
2. 維持費不安のある効率重視層 → ハイブリッド車がブースト
3. Load なしの場合 → ブーストスコア 0
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engine.recommendation_engine import RecommendationEngine, RecommendationRequest


def test_parking_anxiety_boost():
    """テストケース1: 駐車不安 → パノラミックビューモニター搭載車がブースト"""
    print("\n=== Test 1: 駐車不安のあるファミリー層 ===")
    
    engine = RecommendationEngine()
    try:
        # Load なしの推薦
        req_without_load = RecommendationRequest(
            family_size=4,
            budget=3_500_000,
            needs=["safety", "family"],
            detected_loads=[],
        )
        results_without = engine.recommend(req_without_load, top_k=5)
        
        # Load ありの推薦
        req_with_load = RecommendationRequest(
            family_size=4,
            budget=3_500_000,
            needs=["safety", "family"],
            detected_loads=["parking"],
        )
        results_with = engine.recommend(req_with_load, top_k=5)
        
        print("\n[Load なし]")
        for r in results_without[:3]:
            print(f"  {r.model:15s} score={r.score:.3f} | {r.reason}")
        
        print("\n[Load あり: parking]")
        for r in results_with[:3]:
            print(f"  {r.model:15s} score={r.score:.3f} boost={r.load_boost:.3f} | {r.reason}")
            if r.matched_load_features:
                print(f"    -> マッチした機能: {', '.join(r.matched_load_features[:2])}")
        
        # スコアの変化を確認
        boost_applied = any(r.load_boost > 0 for r in results_with)
        if boost_applied:
            print("\n[OK] Load Boost が適用されました")
        else:
            print("\n[WARN] Load Boost が適用されませんでした（該当機能を持つ車種がない可能性）")
    
    finally:
        engine.close()


def test_maintenance_anxiety_boost():
    """テストケース2: 維持費不安 → ハイブリッド車がブースト"""
    print("\n=== Test 2: 維持費不安のある効率重視層 ===")
    
    engine = RecommendationEngine()
    try:
        # Load なしの推薦
        req_without_load = RecommendationRequest(
            family_size=2,
            budget=2_500_000,
            needs=["fuel_efficiency", "safety"],
            detected_loads=[],
        )
        results_without = engine.recommend(req_without_load, top_k=5)
        
        # Load ありの推薦
        req_with_load = RecommendationRequest(
            family_size=2,
            budget=2_500_000,
            needs=["fuel_efficiency", "safety"],
            detected_loads=["maintenance"],
        )
        results_with = engine.recommend(req_with_load, top_k=5)
        
        print("\n[Load なし]")
        for r in results_without[:3]:
            print(f"  {r.model:15s} score={r.score:.3f} | {r.reason}")
        
        print("\n[Load あり: maintenance]")
        for r in results_with[:3]:
            print(f"  {r.model:15s} score={r.score:.3f} boost={r.load_boost:.3f} | {r.reason}")
            if r.matched_load_features:
                print(f"    -> マッチした機能: {', '.join(r.matched_load_features[:2])}")
        
        # スコアの変化を確認
        boost_applied = any(r.load_boost > 0 for r in results_with)
        if boost_applied:
            print("\n[OK] Load Boost が適用されました")
        else:
            print("\n[WARN] Load Boost が適用されませんでした（該当機能を持つ車種がない可能性）")
    
    finally:
        engine.close()


def test_multiple_loads():
    """テストケース3: 複数の Load → 複数のブーストが適用"""
    print("\n=== Test 3: 複数の Load（駐車不安 + 維持費不安） ===")
    
    engine = RecommendationEngine()
    try:
        req = RecommendationRequest(
            family_size=3,
            budget=3_000_000,
            needs=["safety", "fuel_efficiency"],
            detected_loads=["parking", "maintenance"],
        )
        results = engine.recommend(req, top_k=5)
        
        print("\n[Load あり: parking + maintenance]")
        for r in results[:3]:
            print(f"  {r.model:15s} score={r.score:.3f} boost={r.load_boost:.3f}")
            print(f"    -> 理由: {r.reason}")
            if r.matched_load_features:
                print(f"    -> マッチした機能: {', '.join(r.matched_load_features)}")
        
        # 複数ブーストの確認
        multi_boost = any(len(r.matched_load_features) > 1 for r in results)
        if multi_boost:
            print("\n[OK] 複数の Load に対するブーストが適用されました")
        else:
            print("\n[INFO] 単一 Load のブーストのみ適用")
    
    finally:
        engine.close()


def test_no_load():
    """テストケース4: Load なし → ブーストスコア 0"""
    print("\n=== Test 4: Load なし（従来の推薦） ===")
    
    engine = RecommendationEngine()
    try:
        req = RecommendationRequest(
            family_size=4,
            budget=3_500_000,
            needs=["safety", "family"],
            detected_loads=[],
        )
        results = engine.recommend(req, top_k=3)
        
        print("\n[Load なし]")
        for r in results:
            print(f"  {r.model:15s} score={r.score:.3f} boost={r.load_boost:.3f}")
            print(f"    -> 理由: {r.reason}")
        
        # ブーストが 0 であることを確認
        all_zero_boost = all(r.load_boost == 0 for r in results)
        if all_zero_boost:
            print("\n[OK] Load なしの場合、ブーストスコアは 0 です")
        else:
            print("\n[ERROR] Load なしなのにブーストスコアが付いています")
    
    finally:
        engine.close()


if __name__ == "__main__":
    # Neo4j 接続確認
    try:
        engine = RecommendationEngine()
        engine.driver.verify_connectivity()
        print("[OK] Neo4j 接続成功")
        engine.close()
    except Exception as e:
        print(f"[ERROR] Neo4j 接続失敗: {e}")
        print("テストを中止します")
        sys.exit(1)
    
    # Load マッピング設定確認
    config_path = project_root / "config" / "load-feature-mapping.json"
    if config_path.exists():
        print(f"[OK] Load マッピング設定ファイルが存在: {config_path}")
    else:
        print(f"[WARN] Load マッピング設定ファイルが見つかりません: {config_path}")
    
    # テスト実行
    test_no_load()
    test_parking_anxiety_boost()
    test_maintenance_anxiety_boost()
    test_multiple_loads()
    
    print("\n=== すべてのテストが完了しました ===")
