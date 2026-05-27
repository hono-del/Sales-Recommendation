# データベース設計書

> **プロジェクト**: Decision Intelligence — 迷わせないレコメンド  
> **ソース**: `docs/output/detailed_requirements_specification.md` §7  
> **バージョン**: 1.0 | **作成日**: 2026-05-26

---

## 1. 概要

本システムは **二層データモデル** を採用する。

| ストア | 役割 | 読み書き |
|--------|------|----------|
| **Supabase (PostgreSQL)** | デモセッション・回答・プロファイル・イベント | 読み書き |
| **Neo4j** | 購入者ナレッジグラフ（v3 オントロジー） | **読み取りのみ**（デモ中） |
| **静的 JSON** | fallback 用マスタ | 読み取りのみ |

---

## 2. ER 図（Supabase）

```mermaid
erDiagram
    demo_sessions ||--o{ session_answers : "has"
    demo_sessions ||--|| session_profiles : "has"
    demo_sessions ||--o{ session_events : "logs"

    demo_sessions {
        uuid id PK
        timestamptz created_at
        timestamptz updated_at
        varchar delegation_level
        varchar status
        boolean demo_fallback_used
        jsonb metadata
    }

    session_answers {
        uuid id PK
        uuid session_id FK
        int question_index
        varchar question_id
        varchar answer_key
        timestamptz answered_at
    }

    session_profiles {
        uuid session_id PK_FK
        float score_safety
        float score_family
        float score_efficiency
        float score_enjoyment
        float score_adventure
        jsonb mapped_needs
        jsonb mapped_capabilities
        jsonb detected_loads
        timestamptz updated_at
    }

    session_events {
        uuid id PK
        uuid session_id FK
        varchar screen_id
        varchar event_type
        jsonb payload
        int duration_ms
        timestamptz created_at
    }
```

---

## 3. テーブル定義（Supabase / PostgreSQL）

### 3.1 `demo_sessions`

デモ体験の単位。Opening 開始時に 1 レコード作成。

| カラム名 | データ型 | NULL | デフォルト | 制約 | 説明 |
|---------|---------|------|-----------|------|------|
| `id` | `UUID` | NO | `gen_random_uuid()` | PK | セッション識別子（API・FE 共通） |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | — | 作成日時 |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | — | 最終更新（トリガーで自動更新） |
| `delegation_level` | `VARCHAR(20)` | YES | NULL | CHECK: guide/co_pilot/auto | AI Delegation 選択 |
| `status` | `VARCHAR(20)` | NO | `'active'` | CHECK: active/completed/aborted | セッション状態 |
| `demo_fallback_used` | `BOOLEAN` | NO | `false` | — | Neo4j/JSON fallback 使用有無 |
| `metadata` | `JSONB` | YES | NULL | — | オペレーター ID、デモ版番号等 `(拡張用)` |

**インデックス**

```sql
CREATE INDEX idx_demo_sessions_created_at ON demo_sessions (created_at DESC);
CREATE INDEX idx_demo_sessions_status ON demo_sessions (status);
```

---

### 3.2 `session_answers`

Quick Questions（5 問）の各回答。1 問 1 レコード（上書き更新も可）。

| カラム名 | データ型 | NULL | デフォルト | 制約 | 説明 |
|---------|---------|------|-----------|------|------|
| `id` | `UUID` | NO | `gen_random_uuid()` | PK | 回答 ID |
| `session_id` | `UUID` | NO | — | FK → demo_sessions(id) ON DELETE CASCADE | 親セッション |
| `question_index` | `INT` | NO | — | CHECK: 1〜5 | 質問番号 |
| `question_id` | `VARCHAR(50)` | NO | — | — | `q1_value`, `q2_weekend` 等 |
| `answer_key` | `VARCHAR(50)` | NO | — | — | `safety`, `family_center` 等 |
| `answered_at` | `TIMESTAMPTZ` | NO | `now()` | — | 回答日時 |

**ユニーク制約**（同一セッション・同一問は 1 件）

```sql
CREATE UNIQUE INDEX uq_session_question
  ON session_answers (session_id, question_index);
```

**質問 ID マスタ** `(アプリ設定)`

| question_index | question_id | 内容 |
|----------------|-------------|------|
| 1 | `q1_value` | 車に求める価値 |
| 2 | `q2_weekend` | 休日の過ごし方 |
| 3 | `q3_regret` | 避けたい後悔 |
| 4 | `q4_stress` | 移動時のストレス |
| 5 | `q5_ai` | AI との付き合い方 |

---

### 3.3 `session_profiles`

セッションごとの集計スコア・グラフマッピング結果。`session_id` と 1:1。

| カラム名 | データ型 | NULL | デフォルト | 制約 | 説明 |
|---------|---------|------|-----------|------|------|
| `session_id` | `UUID` | NO | — | PK, FK → demo_sessions | — |
| `score_safety` | `DOUBLE PRECISION` | NO | `0` | CHECK: 0〜100 | 安心軸 |
| `score_family` | `DOUBLE PRECISION` | NO | `0` | CHECK: 0〜100 | 家族軸 |
| `score_efficiency` | `DOUBLE PRECISION` | NO | `0` | CHECK: 0〜100 | 効率軸 |
| `score_enjoyment` | `DOUBLE PRECISION` | NO | `0` | CHECK: 0〜100 | 楽しさ軸 |
| `score_adventure` | `DOUBLE PRECISION` | NO | `0` | CHECK: 0〜100 | 冒険軸 |
| `mapped_needs` | `JSONB` | YES | `[]` | — | v3 `Need.name` 配列 |
| `mapped_capabilities` | `JSONB` | YES | `[]` | — | `Capability.name` 配列 |
| `detected_loads` | `JSONB` | YES | `[]` | — | Why Panel 用負荷ラベル |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | — | 最終スコア更新 |

**作成タイミング**: 初回回答 POST 時に UPSERT。

---

### 3.4 `session_events`

画面遷移・操作の監査ログ（KPI 計測・デモ改善用）。

| カラム名 | データ型 | NULL | デフォルト | 制約 | 説明 |
|---------|---------|------|-----------|------|------|
| `id` | `UUID` | NO | `gen_random_uuid()` | PK | — |
| `session_id` | `UUID` | NO | — | FK → demo_sessions | — |
| `screen_id` | `VARCHAR(30)` | NO | — | — | `SCR-01` 〜 `SCR-07` |
| `event_type` | `VARCHAR(30)` | NO | — | — | `enter`, `leave`, `cta_click`, `api_error` |
| `payload` | `JSONB` | YES | NULL | — | 追加コンテキスト |
| `duration_ms` | `INT` | YES | NULL | — | 画面滞在時間（leave 時） |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | — | — |

**インデックス**

```sql
CREATE INDEX idx_session_events_session ON session_events (session_id, created_at);
```

---

## 4. リレーションシップ

| 親 | 子 | 関係 | 削除時 |
|----|-----|------|--------|
| `demo_sessions` | `session_answers` | 1:N | CASCADE |
| `demo_sessions` | `session_profiles` | 1:1 | CASCADE |
| `demo_sessions` | `session_events` | 1:N | CASCADE |

---

## 5. Neo4j グラフスキーマ（参照）

デモ中は **読み取り専用**。詳細は `CLAUDE.md` を参照。

### 5.1 主要ノードラベル

| ラベル | 件数目安 | デモでの用途 |
|--------|---------|-------------|
| `Consumer` | 4,205 | 類似購入者参照（非表示 ID） |
| `Need` | 55 | Quick Questions → マッピング先 |
| `Capability` | 9 | 推薦ロジック・Why Panel |
| `TechnicalFeature` | 411 | 車種機能・グラフ表示 |
| `VehicleModel` | 3,817 | 推薦候補 |
| `VehicleOwnership` | 7,533 | 類似消費者スコア |
| `DecisionStyle` | 6 | `(将来)` ペルソナ分類 |

### 5.2 主要リレーション（v3）

```
Consumer -[:HAS_NEED]-> Need
Consumer -[:OWNED]-> VehicleOwnership -[:OF_MODEL]-> VehicleModel
VehicleModel -[:HAS_FEATURE]-> TechnicalFeature -[:REALIZES]-> Capability
Capability -[:SUPPORTS]-> Need
Capability -[:INFLUENCES]-> EvaluationCriteria
```

### 5.3 デモ用 Cypher パターン

**説明パス取得（graph-path API）**

```cypher
MATCH (v:VehicleModel {name: $vehicle_name})
      -[:HAS_FEATURE]->(tf:TechnicalFeature)
      -[:REALIZES]->(cap:Capability)
      -[:SUPPORTS]->(n:Need)
WHERE n.name IN $mapped_needs
RETURN v, tf, cap, n
LIMIT 50
```

**推薦スコア** — `recommendation_engine.py` 内で実行（v3 対応済み）。

---

## 6. 静的 JSON（fallback）

| ファイル | 用途 |
|---------|------|
| `public/demo/fallback/graph-path.json` | KG 画面固定ノード/エッジ |
| `public/demo/fallback/recommend.json` | 推薦 3 件固定 |
| `config/score-weights.json` | Q 回答 → スコア重み（FE/BE 共通） |
| `config/need-mapping.json` | UI needs → v3 Need.name |

---

## 7. マイグレーション方針

1. Supabase Dashboard または `supabase/migrations/` で SQL 管理
2. RLS（Row Level Security）: デモフェーズは **無効または anon 全許可** `(仮定: 社内デモのみ)`
3. Neo4j は `graph_builder.py` で再構築、デモ DB とは独立

---

## 8. 参考資料

- `docs/output/detailed_requirements_specification.md` §7
- `CLAUDE.md` — グラフスキーマ v3
- `graph/graph_builder.py` — オントロジー定義
