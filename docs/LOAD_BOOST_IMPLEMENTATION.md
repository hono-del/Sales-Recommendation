# Load Boost 機能 実装ガイド

**作成日**: 2026-05-27  
**バージョン**: v1.0  
**対象**: 推薦エンジンへのLoad検出統合

---

## 📋 概要

Quick Questions で検出された **Load（負荷・不安）** を推薦ロジックに統合し、顧客の不安を解消する機能を持つ車種のスコアをブーストする。

### 例
- **Load**: `parking`（駐車・狭い道への不安）
- **推奨機能**: パノラミックビューモニター、バックモニター、360度カメラ
- **効果**: これらの機能を持つ車種のスコアに **+18点** を加算

---

## 🎯 設計方針

### 1. **Load → Feature マッピング**
- 各 Load に対して、解消に役立つ TechnicalFeature をリストアップ
- ブーストスコア（0-20点）を設定
- 対応する Capability も記録（推薦理由生成に使用）

### 2. **スコア計算式の拡張**

```python
# 従来
final_score = need_match_score × 0.45 + 
              feature_score × 0.25 + 
              consumer_similarity × 0.20 + 
              eval_criteria_match × 0.10

# 新規（Load Boost 統合）
base_score = need_match_score × 0.45 + 
             feature_score × 0.25 + 
             consumer_similarity × 0.20 + 
             eval_criteria_match × 0.10

load_boost = Σ(車種が持つ Load 対応機能のブーストポイント)

final_score = min(100, base_score + load_boost)
```

### 3. **推薦理由への反映**

Load ブーストが適用された場合、推薦理由に明記：

```
例: 
「パノラミックビューモニターと360度カメラで、狭い道や駐車時の不安を解消。
運転に自信が持てる先進安全装備を標準搭載。」
```

---

## 🔧 実装ステップ

### Step 1: マッピング設定ファイルの作成

**ファイル**: `config/load-feature-mapping.json`

```json
{
  "version": "1.0",
  "load_to_features": {
    "parking": {
      "features": [
        "パノラミックビューモニター",
        "バックモニター",
        "パーキングセンサー",
        "360度カメラ"
      ],
      "boost_score": 18,
      "capabilities": ["SafetyPerformance", "GeneralPerformance"]
    },
    "fatigue": {
      "features": [
        "アダプティブクルーズコントロール",
        "Honda SENSING",
        "プレミアムシート"
      ],
      "boost_score": 15,
      "capabilities": ["RideComfort", "SafetyPerformance"]
    }
  }
}
```

### Step 2: 推薦エンジンの拡張

**ファイル**: `engine/recommendation_engine.py`

```python
import json
from pathlib import Path

class RecommendationEngine:
    def __init__(self):
        # 既存の初期化
        self.driver = GraphDatabase.driver(...)
        
        # Load マッピングを読み込み
        config_path = Path(__file__).parent.parent / "config" / "load-feature-mapping.json"
        self.load_mapping = json.loads(config_path.read_text(encoding="utf-8"))
    
    def _calculate_load_boost(
        self, 
        vehicle_name: str, 
        detected_loads: list[str]
    ) -> tuple[float, list[str]]:
        """
        車種が持つ Load 対応機能のブーストスコアを計算
        
        Returns:
            (boost_score, matched_features): ブーストポイントとマッチした機能リスト
        """
        if not detected_loads:
            return 0.0, []
        
        # 車種の全機能を取得
        vehicle_features = self._get_vehicle_features(vehicle_name)
        
        total_boost = 0.0
        matched_features = []
        
        for load_key in detected_loads:
            load_config = self.load_mapping["load_to_features"].get(load_key, {})
            boost = load_config.get("boost_score", 0)
            target_features = load_config.get("features", [])
            
            # 部分一致で機能をチェック
            for target in target_features:
                for vehicle_feature in vehicle_features:
                    if target in vehicle_feature or vehicle_feature in target:
                        total_boost += boost
                        matched_features.append(vehicle_feature)
                        break  # 1つの Load につき1回だけブースト
                if matched_features:
                    break
        
        return total_boost, matched_features
    
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
    
    def recommend(
        self,
        needs: list[str],
        detected_loads: list[str] = None,  # 新規パラメータ
        **kwargs
    ) -> list[Recommendation]:
        """
        推薦を実行（Load Boost 対応）
        """
        detected_loads = detected_loads or []
        vehicles = self._get_all_vehicles()
        recommendations = []
        
        for vehicle in vehicles:
            vehicle_name = vehicle["name"]
            
            # 既存のスコア計算
            base_score = self._calculate_base_score(vehicle_name, needs, **kwargs)
            
            # Load Boost を加算
            load_boost, matched_features = self._calculate_load_boost(
                vehicle_name, 
                detected_loads
            )
            
            final_score = min(100.0, base_score + load_boost)
            
            # 推薦理由を生成
            reason = self._generate_reason(
                vehicle_name,
                needs,
                detected_loads,
                matched_features
            )
            
            recommendations.append(
                Recommendation(
                    model=vehicle_name,
                    score=final_score,
                    reason=reason,
                    load_boost=load_boost,  # デバッグ用
                    matched_load_features=matched_features  # デバッグ用
                )
            )
        
        # スコア順にソート
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:3]
```

### Step 3: API エンドポイントの更新

**ファイル**: `api/demo/router.py`

```python
@router.post("/sessions/{session_id}/recommend")
def post_recommend(session_id: str):
    session = _get_session(session_id)
    profile = session.get("profile", {})
    
    # Need を取得
    ui_needs = session.get("ui_needs", ["safety", "family", "comfort"])
    
    # Load を取得（新規）
    detected_loads = session.get("detected_loads", [])
    
    # 推薦エンジン呼び出し（Load を渡す）
    recommendations = engine.recommend(
        needs=ui_needs,
        detected_loads=detected_loads,  # Load を渡す
        family_size=session.get("family_size", 3),
        budget=session.get("budget", 3000000)
    )
    
    return {
        "session_id": session_id,
        "recommendations": [
            {
                "model": r.model,
                "score": r.score,
                "reason": r.reason,
                "load_boost": r.load_boost  # デバッグ情報
            }
            for r in recommendations
        ]
    }
```

### Step 4: 推薦理由生成の強化

```python
def _generate_reason(
    self,
    vehicle_name: str,
    needs: list[str],
    detected_loads: list[str],
    matched_load_features: list[str]
) -> str:
    """Load 対応機能を含めた推薦理由を生成"""
    
    reasons = []
    
    # 既存: Need ベースの理由
    if "safety" in needs:
        reasons.append("先進安全装備で運転をサポート")
    
    # 新規: Load ベースの理由
    if "parking" in detected_loads and matched_load_features:
        reasons.append(
            f"{matched_load_features[0]}で駐車や狭い道の不安を解消"
        )
    
    if "fatigue" in detected_loads and matched_load_features:
        reasons.append(
            "アダプティブクルーズで長距離運転の疲労を軽減"
        )
    
    if "maintenance" in detected_loads:
        reasons.append(
            "ハイブリッドシステムで維持費を抑えられる"
        )
    
    return "。".join(reasons[:3]) + "。"
```

---

## 📊 Load → Feature マッピング一覧

| Load | 日本語 | 推奨機能 | ブースト | Capability |
|------|--------|---------|---------|------------|
| **parking** | 駐車・狭い道への不安 | パノラミックビューモニター、バックモニター、360度カメラ | +18 | SafetyPerformance |
| **fatigue** | 長距離移動による疲労 | アダプティブクルーズコントロール、Honda SENSING、プレミアムシート | +15 | RideComfort, SafetyPerformance |
| **traffic** | 渋滞ストレス | アダプティブクルーズコントロール、渋滞追従機能 | +12 | FuelEfficiency, RideComfort |
| **difficult_operation** | 操作の難しさ | Honda SENSING、ヘッドアップディスプレイ、電動パーキングブレーキ | +14 | SafetyPerformance, TechInnovation |
| **too_much_info** | 情報過多による判断負荷 | シンプルインターフェース、音声認識システム | +10 | TechInnovation |
| **family_dissatisfaction** | 家族同乗時の不満リスク | 3列シート、スライドドア、後席モニター | +16 | FamilyFriendly, SpaceUtility |
| **maintenance** | 維持費への不安 | ハイブリッドシステム、e:HEV、電動パワートレイン | +15 | FuelEfficiency |
| **feature_lack** | 機能不足による後悔 | Honda SENSING、先進安全装備、コネクテッド機能 | +12 | TechInnovation, SafetyPerformance |
| **unused** | 使わない設備への投資 | シートアレンジ、コンパクト設計、実用装備 | +10 | FuelEfficiency, SpaceUtility |
| **boredom** | すぐ飽きるリスク | スポーティデザイン、パドルシフト、走行性能 | +13 | DesignAppeal, GeneralPerformance |

---

## 🎯 期待される効果

### 1. **推薦精度の向上**
- Need だけでなく、**不安・負荷も考慮**した推薦
- 顧客の潜在的な課題に対応

### 2. **説明力の強化**
- 「なぜこの車種か」の理由に、**不安解消の視点**を追加
- 「パノラミックビューモニターで駐車不安を解消」のような具体的な訴求

### 3. **差別化の明確化**
- 同じ Need でも、Load が異なれば異なる車種を推薦
- よりパーソナライズされた提案

### 4. **販売トークへの活用**
- Dealer Talk 生成時に、Load 対応機能を強調
- 顧客の不安に直接訴求するトーク

---

## 🧪 テスト例

### テストケース 1: 駐車不安のあるファミリー層

```python
# 入力
needs = ["safety", "family"]
detected_loads = ["parking", "family_dissatisfaction"]

# 期待される結果
# - パノラミックビューモニター搭載車のスコアが +18
# - スライドドア搭載車のスコアが +16
# - 推薦: ステップワゴン（両方の機能あり） → スコア高
```

### テストケース 2: 維持費不安のある効率重視層

```python
# 入力
needs = ["fuel_efficiency", "safety"]
detected_loads = ["maintenance"]

# 期待される結果
# - ハイブリッド車のスコアが +15
# - 推薦: FIT e:HEV → スコア高
# - 理由: 「ハイブリッドシステムで維持費を抑えられる」
```

---

## 📝 実装チェックリスト

- [x] `config/load-feature-mapping.json` 作成
- [x] `engine/recommendation_engine.py` に `_calculate_load_boost` 追加
- [x] `engine/recommendation_engine.py` に `_get_vehicle_features` 追加
- [x] `recommend()` メソッドに `detected_loads` パラメータ追加
- [x] `_generate_load_reason()` を Load 対応機能を含むように作成
- [x] `api/demo/recommend_service.py` の推薦ロジックを更新
- [x] `tests/test_load_boost.py` テストケース作成
- [x] `docs/QUICK_QUESTIONS_LOGIC.md` に Load Boost 説明追加

## ✅ 実装完了

**完了日**: 2026-05-27

### 実装内容

1. **Load → Feature マッピング設定** (`config/load-feature-mapping.json`)
   - 10種類の Load に対する推奨機能を定義
   - ブーストスコア（0-20点）を設定

2. **推薦エンジン拡張** (`engine/recommendation_engine.py`)
   - `_get_vehicle_features()` - 車種の機能リストを取得
   - `_calculate_load_boost()` - Load ブーストスコアを計算
   - `_generate_load_reason()` - Load に基づく推薦理由を生成
   - `recommend()` メソッドに Load Boost ロジックを統合

3. **API 更新** (`api/demo/recommend_service.py`)
   - セッションの `detected_loads` を `RecommendationRequest` に渡す
   - 推薦結果に `load_boost` と `matched_load_features` を追加

4. **テストケース** (`tests/test_load_boost.py`)
   - 駐車不安のあるファミリー層
   - 維持費不安のある効率重視層
   - 複数の Load
   - Load なし（従来の推薦）

5. **ドキュメント更新**
   - `docs/QUICK_QUESTIONS_LOGIC.md` - Load Boost の説明追加
   - `docs/LOAD_BOOST_IMPLEMENTATION.md` - 実装ガイド作成

---

## 🔗 関連ファイル

- `config/load-feature-mapping.json` - Load → Feature マッピング
- `config/score-weights.json` - Load 検出ルール
- `engine/recommendation_engine.py` - 推薦エンジン本体
- `api/demo/router.py` - API エンドポイント
- `docs/QUICK_QUESTIONS_LOGIC.md` - Quick Questions 設計書

---

**最終更新**: 2026-05-27  
**ステータス**: 設計完了・実装待ち
