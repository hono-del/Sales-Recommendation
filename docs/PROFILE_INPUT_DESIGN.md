# Profile Input 画面設計

**作成日**: 2026-05-27  
**バージョン**: Phase 4.1  
**目的**: ユーザーから人数・予算を直接ヒアリングし、Quick Questions と組み合わせて推薦精度を向上

---

## 📋 画面フロー

```
Opening → Profile Input → Questions (5問) → Delegation → Graph → Recommend → Dealer → Closing
         ↑ 新規追加
```

---

## 🎨 画面デザイン

### Profile Input 画面

**タイトル**: 「まず、基本的なことを教えてください」

#### 入力項目1: 乗車人数

**質問**: 「普段、何人で車に乗ることが多いですか？」

**選択肢** (ボタン形式):
```
┌─────────┬─────────┬─────────┬─────────┬─────────┐
│  1人    │  2人    │  3-4人  │  5-6人  │  7人以上 │
└─────────┴─────────┴─────────┴─────────┴─────────┘
```

**補足テキスト** (小さく):
「※ 家族構成や普段の乗車人数をお選びください」

#### 入力項目2: 予算

**質問**: 「予算の目安を教えてください」

**選択肢** (ボタン形式):
```
┌───────────┬───────────┬───────────┬───────────┬───────────┐
│ ~200万円  │ 200-300万 │ 300-400万 │ 400-500万 │ 500万円~  │
└───────────┴───────────┴───────────┴───────────┴───────────┘
```

**補足テキスト** (小さく):
「※ あくまで目安です。ご希望に応じて柔軟に提案します」

#### ボタン

```
┌────────────────────┐
│   次へ（Questions）  │  ← 両方選択後に有効化
└────────────────────┘
```

---

## 🔧 データ構造

### API Request Body

```json
{
  "session_id": "uuid",
  "family_size": 4,
  "budget_range": "300-400"
}
```

### セッションストア

```json
{
  "session_id": "uuid",
  "status": "profile_input_complete",
  "family_size": 4,
  "budget_range": "300-400",
  "budget_min": 3000000,
  "budget_max": 4000000,
  "answers": [],
  "profile": {}
}
```

---

## 🎯 推薦ロジックへの活用

### 1. 乗車人数の活用

#### 基本フィルタリング

```python
# 推薦エンジンで車種をフィルタリング
if req.family_size > 0 and seating > 0 and seating < req.family_size:
    continue  # 定員不足の車種をスキップ
```

#### Quick Questions との組み合わせ

| 入力人数 | Q2: 休日の過ごし方 | 推薦への影響 |
|---------|-------------------|-------------|
| 3-4人 | family_center（家族中心） | ファミリー向け車種を優先（ミニバン、スライドドア） |
| 3-4人 | solo（一人時間） | 趣味・レジャーにも対応（SUV、ラゲッジ広い） |
| 3-4人 | active（アクティブ） | アウトドア対応（4WD、オフロード性能） |
| 1-2人 | solo | コンパクトカー、スポーツカー優先 |
| 1-2人 | hobby（趣味） | 走りや個性重視の車種 |
| 5-6人 | family_center | 3列シート必須（ステップワゴン、フリードなど） |

**実装例**:

```python
def _boost_for_family_usage(
    self, 
    family_size: int, 
    weekend_activity: str, 
    vehicle_features: list[str]
) -> float:
    """
    人数 × 休日の過ごし方で追加ブースト
    """
    boost = 0.0
    
    # 家族4人 + 家族中心 → ファミリー機能にブースト
    if family_size >= 3 and weekend_activity == "family_center":
        if any("スライドドア" in f or "3列シート" in f for f in vehicle_features):
            boost += 0.10
    
    # 家族4人 + 一人時間 → 多用途対応にブースト
    elif family_size >= 3 and weekend_activity == "solo":
        if any("ラゲッジ" in f or "SUV" in f for f in vehicle_features):
            boost += 0.08
    
    # 1-2人 + 趣味 → 個性・走りにブースト
    elif family_size <= 2 and weekend_activity in ["hobby", "solo"]:
        if any("スポーティ" in f or "走行性能" in f for f in vehicle_features):
            boost += 0.08
    
    return boost
```

### 2. 予算の活用

#### 基本フィルタリング

```python
# 予算範囲を設定（柔軟性あり）
budget_min = req.budget_min
budget_max = req.budget_max * 1.2  # 20%オーバーまで許容

if max_price > 0 and (max_price < budget_min * 0.8 or max_price > budget_max):
    continue  # 予算から大きく外れる車種をスキップ
```

#### Quick Questions との組み合わせ

| 予算範囲 | Q1: 車に求める価値 | 推薦への影響 |
|---------|-------------------|-------------|
| 200-300万 | efficiency（効率） | **予算下限寄り**を優先（180-250万）、燃費性能重視 |
| 200-300万 | safety（安心） | **予算上限まで**活用（250-320万）、安全装備充実 |
| 200-300万 | status（ステータス） | **予算上限+α**を提案（280-350万）、上質感重視 |
| 400-500万 | efficiency（効率） | **予算下限寄り**（350-450万）、ハイブリッド優先 |
| 400-500万 | enjoyment（楽しさ） | **予算上限まで**（450-550万）、走行性能・装備充実 |

**実装例**:

```python
def _adjust_budget_by_value(
    self, 
    budget_min: int, 
    budget_max: int, 
    value_axis: str
) -> tuple[int, int]:
    """
    価値観に応じて予算範囲を調整
    """
    if value_axis == "efficiency":
        # 効率重視 → 下限寄り
        return budget_min, int(budget_max * 0.9)
    
    elif value_axis == "status":
        # ステータス重視 → 上限+20%
        return int(budget_min * 1.1), int(budget_max * 1.2)
    
    elif value_axis == "safety":
        # 安心重視 → 上限まで活用
        return budget_min, int(budget_max * 1.1)
    
    # デフォルト
    return budget_min, budget_max
```

### 3. 推薦理由の生成

人数・予算を考慮した推薦理由を生成：

```python
def _generate_reason_with_profile(
    self,
    family_size: int,
    budget_range: str,
    value_axis: str,
    vehicle_name: str
) -> str:
    """
    プロファイルを考慮した推薦理由
    """
    reasons = []
    
    # 人数ベースの理由
    if family_size >= 5:
        reasons.append(f"{family_size}人乗車に対応した広々空間")
    elif family_size >= 3:
        reasons.append(f"家族{family_size}人で快適に移動")
    
    # 価値観 × 予算の理由
    if value_axis == "efficiency":
        reasons.append(f"予算内で燃費・維持費を抑えられる")
    elif value_axis == "safety":
        reasons.append(f"予算内で最高レベルの安全装備")
    
    return "、".join(reasons)
```

---

## 📊 具体例

### 例1: 家族4人 + 予算300万 + 家族中心 + 効率重視

**入力**:
- 人数: 3-4人
- 予算: 300-400万

**Q1**: efficiency（効率）
**Q2**: family_center（家族中心）

**推薦ロジック**:
1. 定員: 5人乗り以上
2. 予算: 250-360万（効率重視で下限寄り）
3. ブースト: ファミリー機能 + 燃費性能
4. 推薦理由: 「家族4人で快適に移動、予算内で燃費・維持費を抑えられる」

**推薦結果**: FIT（ハイブリッド）、フリード、ステップワゴン

---

### 例2: 1人 + 予算400万 + 趣味 + 楽しさ重視

**入力**:
- 人数: 1人
- 予算: 400-500万

**Q1**: enjoyment（楽しさ）
**Q2**: hobby（趣味）

**推薦ロジック**:
1. 定員: 制約なし（コンパクトカーも可）
2. 予算: 400-550万（楽しさ重視で上限まで）
3. ブースト: 走行性能 + デザイン性
4. 推薦理由: 「走りを楽しめる個性的なモデル、予算内で最高の装備」

**推薦結果**: シビック TYPE R、ZR-V、CR-V（高グレード）

---

### 例3: 家族5人 + 予算350万 + 一人時間 + 冒険重視

**入力**:
- 人数: 5-6人
- 予算: 300-400万

**Q1**: adventure（冒険）
**Q2**: solo（一人時間）

**推薦ロジック**:
1. 定員: 7人乗り（3列シート必須）
2. 予算: 300-420万
3. ブースト: 多用途対応（ファミリー + アウトドア）
4. 推薦理由: 「家族5人で移動でき、一人でアウトドアにも対応」

**推薦結果**: ステップワゴン（4WD）、フリード（3列シート）

---

## 🔗 API 設計

### POST /api/demo/sessions/{session_id}/profile

**Request Body**:
```json
{
  "family_size": 4,
  "budget_range": "300-400"
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "status": "profile_input_complete",
  "family_size": 4,
  "budget_min": 3000000,
  "budget_max": 4000000,
  "next_screen": "questions"
}
```

---

## 📝 実装ファイル

### フロントエンド
- `demo-web/src/app/demo/profile/page.tsx` - Profile Input 画面
- `demo-web/src/components/demo/ProfileInputClient.tsx` - クライアントコンポーネント

### バックエンド
- `api/demo/router.py` - `/sessions/{session_id}/profile` エンドポイント追加
- `api/demo/session_store.py` - `set_profile_input()` メソッド追加
- `engine/recommendation_engine.py` - 人数・予算ベースのフィルタリング・ブースト追加

---

## ✅ 実装チェックリスト

- [x] Profile Input 画面（フロントエンド）
  - `demo-web/src/app/demo/profile/page.tsx`
  - `demo-web/src/components/demo/ProfileInputClient.tsx`
- [x] API エンドポイント `/sessions/{session_id}/profile`
  - `api/demo/router.py` - `post_profile_input` エンドポイント
- [x] セッションストアに `family_size`, `budget_range` 保存
  - `api/demo/session_store.py` - `set_profile_input()` メソッド
- [x] 推薦エンジンに人数・予算フィルタリング追加
  - `engine/recommendation_engine.py` - 予算範囲フィルタリング
  - `api/demo/recommend_service.py` - セッションから人数・予算取得
- [ ] Quick Questions との組み合わせロジック実装（Phase 4.2）
- [ ] 推薦理由生成の拡張（Phase 4.2）
- [ ] テストケース作成
- [ ] ドキュメント更新

---

**最終更新**: 2026-05-27  
**ステータス**: Phase 4.1 実装完了（基本機能）・Phase 4.2 実装待ち（組み合わせロジック）
