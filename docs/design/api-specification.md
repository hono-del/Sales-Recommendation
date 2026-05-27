# API 仕様書

> **プロジェクト**: Decision Intelligence — 迷わせないレコメンド  
> **ベース URL**: `{API_URL}`（例: `http://localhost:8000`）  
> **ソース**: `docs/output/detailed_requirements_specification.md` §8  
> **バージョン**: 1.0 | **作成日**: 2026-05-26

---

## 1. 設計原則

| 原則 | 内容 |
|------|------|
| **スタイル** | RESTful。リソース名は複数形・kebab-case |
| **形式** | リクエスト/レスポンスは `application/json`（UTF-8） |
| **エラー** | HTTP ステータス + `{ "detail": "..." }`（FastAPI 標準） |
| **バージョン** | プレフィックス `/api/demo`（新規）、既存はルート直下 |
| **日時** | ISO 8601（UTC）、例: `2026-05-26T06:00:00Z` |
| **ID** | セッションは UUID v4 |

---

## 2. 認証・認可

| フェーズ | 方式 | 説明 |
|---------|------|------|
| **デモ（Phase 1〜3）** | **なし** `(仮定)` | 社内ショールーム・ローカルネットのみ |
| **将来** | API Key ヘッダー `X-API-Key` または Supabase JWT | 本番化時に導入 |

**CORS**

```
Access-Control-Allow-Origin: {NEXT_PUBLIC_VERCEL_URL}
Access-Control-Allow-Methods: GET, POST, PATCH, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

---

## 3. 共通レスポンス

### 3.1 エラー

| HTTP | 意味 | 例 |
|------|------|-----|
| 400 | バリデーションエラー | 未回答で遷移 |
| 404 | セッション未存在 | 無効 session_id |
| 503 | Neo4j 接続不可 | `demo_fallback` 推奨を FE に返す場合あり |
| 500 | サーバー内部エラー | — |

```json
{
  "detail": "Session not found: 550e8400-e29b-41d4-a716-446655440000"
}
```

### 3.2 ヘルスチェック

#### `GET /health`

| 項目 | 内容 |
|------|------|
| **説明** | API・Neo4j 疎通確認 |
| **認証** | 不要 |

**Response 200**

```json
{
  "status": "ok",
  "neo4j": "connected"
}
```

`neo4j` が `unavailable` の場合も 200 を返し、FE はデモモードへ `(推奨)`。

---

## 4. デモ API（新規）

### 4.1 セッション作成

#### `POST /api/demo/sessions`

| 項目 | 内容 |
|------|------|
| **説明** | 新規デモセッションを作成 |
| **Body** | 空オブジェクト可 |

**Request**

```json
{}
```

**Response 201**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-05-26T06:00:00Z",
  "status": "active"
}
```

---

### 4.2 回答登録

#### `POST /api/demo/sessions/{session_id}/answers`

| 項目 | 内容 |
|------|------|
| **説明** | Quick Questions の回答を登録し、プロファイルを再計算 |
| **Path** | `session_id`: UUID |

**Request**

```json
{
  "question_index": 1,
  "question_id": "q1_value",
  "answer_key": "safety"
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `question_index` | int | Yes | 1〜5 |
| `question_id` | string | Yes | 質問マスタ ID |
| `answer_key` | string | Yes | 選択肢キー |

**Response 200**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "profile": {
    "score_safety": 84,
    "score_family": 72,
    "score_efficiency": 65,
    "score_enjoyment": 42,
    "score_adventure": 28
  },
  "mapped_needs": ["ChildSafety", "DrivingConfidence", "FamilyComfort"],
  "mapped_capabilities": ["SafetyPerformance", "FamilyFriendly"]
}
```

---

### 4.3 Delegation 設定

#### `PATCH /api/demo/sessions/{session_id}/delegation`

**Request**

```json
{
  "delegation_level": "co_pilot"
}
```

| 値 | 説明 |
|-----|------|
| `guide` | 候補のみ |
| `co_pilot` | 伴走（デフォルト推奨） |
| `auto` | 最適案 |

**Response 200**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "delegation_level": "co_pilot",
  "message": "AIが伴走しながら、一緒に納得解を探します。"
}
```

---

### 4.4 グラフパス取得

#### `GET /api/demo/sessions/{session_id}/graph-path`

| 項目 | 内容 |
|------|------|
| **説明** | KG Visualization 用 nodes/edges/why_panel |
| **Query** | `top_model` (optional): 推薦 1 位車種名 |

**Response 200（成功）**

```json
{
  "demo_fallback": false,
  "nodes": [
    {
      "id": "person",
      "type": "person",
      "label": "あなた",
      "subtype": "Family Oriented Executive"
    },
    {
      "id": "value_safety",
      "type": "value",
      "label": "安心"
    },
    {
      "id": "load_fatigue",
      "type": "load",
      "label": "疲労"
    },
    {
      "id": "feature_adas",
      "type": "feature",
      "label": "ADAS"
    },
    {
      "id": "vehicle_vezel",
      "type": "vehicle",
      "label": "VEZEL",
      "score": 0.92
    }
  ],
  "edges": [
    { "source": "person", "target": "value_safety", "label": "重視" },
    { "source": "value_safety", "target": "load_fatigue", "label": "軽減したい" },
    { "source": "load_fatigue", "target": "feature_adas", "label": "実現" },
    { "source": "feature_adas", "target": "vehicle_vezel", "label": "搭載" }
  ],
  "why_panel": {
    "values": [
      { "key": "safety", "label": "安心", "percent": 92 },
      { "key": "family", "label": "家族時間", "percent": 84 }
    ],
    "loads": [
      "長距離移動による疲労",
      "情報量増加による判断負荷",
      "家族同乗時の安心ニーズ"
    ],
    "logic": "家族利用 × 疲労軽減 × 後悔回避 → ADAS, 静粛性, 操作支援を重視"
  }
}
```

**Response 200（fallback）**

```json
{
  "demo_fallback": true,
  "nodes": [ "..." ],
  "edges": [ "..." ],
  "why_panel": { "..." }
}
```

---

### 4.5 画面イベント記録

#### `POST /api/demo/sessions/{session_id}/events`

**Request**

```json
{
  "screen_id": "SCR-04",
  "event_type": "enter",
  "payload": {},
  "duration_ms": null
}
```

**Response 201**

```json
{
  "id": "event-uuid",
  "created_at": "2026-05-26T06:05:00Z"
}
```

---

### 4.6 販売店トーク生成

#### `POST /api/demo/sessions/{session_id}/dealer-talk`

**Request**

```json
{
  "top_model": "VEZEL",
  "delegation_level": "co_pilot"
}
```

**Response 200**

```json
{
  "insight": {
    "customer_type": "家族重視",
    "scenes": ["週末利用", "長距離移動"],
    "anxieties": ["疲労", "後悔", "家族安心"],
    "values": ["安心", "家族時間", "効率"]
  },
  "talk_script": "週末の長距離移動が多いとのことなので、単にスペックだけでなく、疲れにくさが重要になると思います。\n\nまたご家族での利用を考えると、安心感や静粛性との相性が良いモデルが満足度につながりやすいです。",
  "generated_by": "template"
}
```

`generated_by`: `template` | `claude`

---

## 5. 既存 API（拡張・再利用）

### 5.1 推薦

#### `POST /recommend`

| 項目 | 内容 |
|------|------|
| **説明** | v3 オントロジー対応推薦エンジン（既存拡張） |

**Request**

```json
{
  "family_size": 4,
  "budget": 10000000,
  "needs": ["safety", "space", "family"],
  "usage": "family_use",
  "delegation_level": "co_pilot",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `family_size` | int | Yes | 家族人数 |
| `budget` | int | Yes | 予算（円） |
| `needs` | string[] | Yes | UI ニーズキー |
| `usage` | string | No | 用途コード |
| `delegation_level` | string | No | 表示制御用 |
| `session_id` | string | No | ログ紐付け |

**Response 200**

```json
{
  "recommendations": [
    {
      "model": "VEZEL",
      "score": 0.857,
      "reason": "ニーズに100%マッチ、同様の家族構成の3名が選択",
      "archetype": "安心重視型",
      "similar_consumers": ["honda_web_1128"],
      "quick_grade": "標準グレード",
      "price_range": "",
      "fuel_type": "",
      "seating_capacity": 0,
      "appeal_points": []
    },
    {
      "model": "FIT",
      "score": 0.875,
      "reason": "ニーズに100%マッチ",
      "archetype": "バランス型",
      "similar_consumers": [],
      "appeal_points": []
    },
    {
      "model": "CR-V",
      "score": 0.808,
      "reason": "同様の家族構成の購入者が多い",
      "archetype": "バランス型",
      "similar_consumers": [],
      "appeal_points": []
    }
  ],
  "excluded": [
    {
      "model": "Premium Luxury",
      "reason": "利用文脈との一致度が低い"
    },
    {
      "model": "High Performance",
      "reason": "利用頻度に対してオーバースペック"
    }
  ]
}
```

**注意**: `score` は 0.0〜1.0。FE 表示は `Math.round(score * 100)`。

---

### 5.2 その他（PoC 既存・デモでは未使用可）

| メソッド | パス | 用途 |
|---------|------|------|
| POST | `/explain` | 車種説明 LLM |
| POST | `/similar_stories` | 類似購入者ストーリー |
| GET | `/graph/stats` | グラフ統計 |
| POST | `/graph/cypher` | 管理用 Cypher（デモでは非公開） |

---

## 6. エンドポイント一覧

| # | メソッド | パス | 説明 | MVP |
|---|---------|------|------|-----|
| 1 | GET | `/health` | ヘルスチェック | Yes |
| 2 | POST | `/api/demo/sessions` | セッション作成 | Yes |
| 3 | POST | `/api/demo/sessions/{id}/answers` | 回答登録 | Yes |
| 4 | PATCH | `/api/demo/sessions/{id}/delegation` | Delegation | Yes |
| 5 | GET | `/api/demo/sessions/{id}/graph-path` | KG データ | Phase 2 |
| 6 | POST | `/api/demo/sessions/{id}/events` | イベントログ | Should |
| 7 | POST | `/api/demo/sessions/{id}/dealer-talk` | トーク生成 | Phase 3 |
| 8 | POST | `/recommend` | 推薦 | Yes |

---

## 7. 参考資料

- `api/api_server.py`
- `recommendation_engine.py`
- OpenAPI: `http://localhost:8000/docs`（uvicorn 起動時）
