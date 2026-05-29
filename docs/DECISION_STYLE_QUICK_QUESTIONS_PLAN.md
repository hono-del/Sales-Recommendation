# Quick Questions による意思決定スタイル判定 — 設計計画

**作成日**: 2026-05-28  
**バージョン**: v1.0（計画）  
**対象**: デモ Web（Quick Questions）→ セッション → 推薦・説明 UI  
**KG 参照**: `DecisionStyle` ノード 6 種（`graph/graph_builder.py` の `DECISION_STYLE_MASTER`）

---

## 1. 目的

### 1.1 やりたいこと

来訪者（デモユーザー）が Quick Questions に答えるだけで、ナレッジグラフ上の **6 つの意思決定スタイル（DecisionStyle）のどれに近いか** を推定し、以下に活用する。

| 活用先 | 内容 |
|--------|------|
| **セッション** | `decision_style`（name）, `decision_style_label`（日本語）, `decision_style_confidence` |
| **推薦** | `Capability -[:APPEALS_TO]-> DecisionStyle` を考慮した説明・スコア補正 |
| **UI** | 「あなたの決め方は〇〇型」表示、販売トーク・情報提示のトーン調整 |
| **KG 整合** | 4,205 購入者の `Consumer -[:HAS_DECISION_STYLE]-> DecisionStyle` と同じ語彙体系 |

### 1.2 やらないこと（本計画の範囲外）

- 購入者レビュー全文の LLM 分類の再実装（既存 `batch_llm_extractor.py` は維持）
- 6 型以外の新スタイル追加
- 臨床心理レベルの診断（デモ向け **傾向推定** に留める）

### 1.3 制約

| 制約 | 方針 |
|------|------|
| 体験時間 | 現状 5 問（約 2.5 分）+ **新規 2 問**（約 +1 分）= **7 問・4 分以内** |
| 設問形式 | 既存と同様 **単一選択・5 択**（実装・UI の一貫性） |
| オントロジー | KG の `name`（英語）に **必ずマッピング**（`Maximizer` 等） |
| 説明可能性 | 「この回答 → このスタイルに +N 点」を JSON で明示 |

---

## 2. 参照：KG の 6 意思決定スタイル

| name（KG） | label（日本語） | 行動の特徴（要約） | 好む情報 |
|------------|----------------|-------------------|----------|
| **Maximizer** | 徹底比較型 | 多数比較・後悔回避・調査重視 | 比較表・スペック・ランキング |
| **Satisficer** | 十分型 | 基準を満たせば決定・比較数を抑える | おすすめパッケージ・要点まとめ |
| **Authority-driven** | 権威依存型 | 専門家・ブランド・評価を信頼 | 受賞・専門レビュー・実績 |
| **Delegator** | 委任型 | 他者に評価・決定を任せる | スタッフおすすめ・人気構成 |
| **Intuitive** | 直感型 | 感触・デザイン・体験重視 | 試乗・ストーリー・ビジュアル |
| **Impulsive** | 衝動型 | 即決・キャンペーン敏感 | 限定・値引き・在庫 |

**KG 上の購入者分布（参考・2026-05 時点）**

| スタイル | 人数 | 割合 |
|----------|------|------|
| Intuitive | 1,405 | 33% |
| Maximizer | 950 | 23% |
| Authority-driven | 828 | 20% |
| Satisficer | 624 | 15% |
| Impulsive | 358 | 9% |
| Delegator | 40 | **1%** |

※ Delegator は稀少。**誤判定を抑えるガード**が必要。

---

## 3. 設計方針

### 3.1 ハイブリッド方式（推奨）

| 層 | 内容 |
|----|------|
| **A. 専用設問（新規 2 問）** | 購買プロセス・情報嗜好を **直接** 聞く（判定の主軸） |
| **B. 既存設問の副次シグナル** | q3 / q4 / q5 から **弱い重み** で補正 |
| **C. ルールガード** | Delegator・Impulsive の **過剰判定を抑制** |

価値観 5 軸（safety / family 等）だけでは 6 スタイルを安定分離できないため、**専用設問を必須**とする。

### 3.2 既存 5 問との役割分担

| 設問 | 現状の役割 | 意思決定スタイルとの関係 |
|------|------------|-------------------------|
| q1_value | 価値観 5 軸 | **直接は使わない**（価値観≠決め方） |
| q2_weekend | 生活文脈 | 副次シグナルなし（または極小） |
| q3_regret | 不安・Load | `feature_lack` → Maximizer 弱め |
| q4_stress | 負荷 | `too_much_info` → Maximizer or Satisficer |
| q5_ai | 委任レベル | `ai_decide` → Delegator / Satisficer 補正 |

---

## 4. 新規設問案

### 4.1 q6_decision_process（購買プロセス — **主設問**）

**質問文**

> これまで、車や高額な買い物を決めるとき、**いちばん近い**のはどれですか？

| key | 表示ラベル | 主加点（style → 点数） |
|-----|------------|------------------------|
| `compare_many` | 候補をたくさん比較してから決める | Maximizer **+30** |
| `good_enough` | 必要な条件が揃ったら、そこで決める | Satisficer **+30** |
| `trust_expert` | 専門家の評価・ランキング・ブランドを重視する | Authority-driven **+30** |
| `ask_others` | 家族や販売員の「おすすめ」で決める | Delegator **+28**, Authority-driven +5 |
| `first_feeling` | 第一印象や試乗の「感触」で決める | Intuitive **+30** |
| `quick_deal` | セールや雰囲気で、その場の勢いで決める | Impulsive **+30** |

**設計意図**: `decision_behavior` の各スタイル定義と 1:1 で対応させ、ユーザーが自己認識しやすい行動文にする。

---

### 4.2 q7_info_preference（情報嗜好 — **副主設問**）

**質問文**

> 車を選ぶとき、**いちばん役立つ**情報はどれですか？

| key | 表示ラベル | 主加点 |
|-----|------------|--------|
| `spec_table` | 詳しいスペック表・複数車の比較 | Maximizer **+25** |
| `shortlist` | 「おすすめ 3 台」の要点まとめ | Satisficer **+22**, Delegator +8 |
| `awards_expert` | 安全評価・受賞・専門家の解説 | Authority-driven **+25** |
| `people_pick` | 販売員・家族・友人のおすすめ | Delegator **+25**, Authority-driven +5 |
| `experience` | 試乗・デザイン・乗った感じ | Intuitive **+25** |
| `offer_now` | 今だけのキャンペーン・在庫・値引き | Impulsive **+25** |

**設計意図**: `information_preference` と整合。q6 と組み合わせて **二軸確認** し、単一設問の誤判定を減らす。

---

### 4.3 既存設問からの補正（副次シグナル）

`config/decision-style-weights.json`（新規）に以下を定義。

#### q3_regret

| 選択肢 | 補正 |
|--------|------|
| `feature_lack` | Maximizer +8（「足りない」を恐れる） |
| `unused` | Satisficer +6 |
| `boredom` | Impulsive +6, Intuitive +4 |

#### q4_stress

| 選択肢 | 補正 |
|--------|------|
| `too_much_info` | Satisficer +10（情報を減らしたい）, Maximizer +4（比較はするが負荷） |
| `difficult_operation` | Authority-driven +6（頼れる仕組み志向） |

#### q5_ai（`config/questions.json` に q5 を追加する前提）

| 選択肢 | 補正 |
|--------|------|
| `ai_decide` | Delegator +12, Satisficer +8 |
| `ai_candidates` | Maximizer +6, Authority-driven +6 |
| `self_decide` | Intuitive +8, Impulsive +6 |

**q5 文言案**

> 車選びで AI に任せたいことは？

| key | ラベル |
|-----|--------|
| `ai_decide` | 条件を伝えたら、最終案まで決めてほしい |
| `ai_candidates` | 候補を絞って、比較の材料を出してほしい |
| `self_decide` | 参考程度にして、最後は自分で決める |

---

## 5. 判定ロジック

### 5.1 スコアリング（擬似コード）

```python
STYLES = [
    "Maximizer", "Satisficer", "Authority-driven",
    "Delegator", "Intuitive", "Impulsive",
]

raw = {s: 0.0 for s in STYLES}
decay = 0.92  # 既存 profile と同じ（後の回答ほど重視）

for i, answer in enumerate(ordered_answers):
    factor = decay ** (len(ordered_answers) - 1 - i)
    weights = DECISION_STYLE_WEIGHTS[answer.question_id][answer.answer_key]
    for style, delta in weights.items():
        raw[style] += delta * factor

# 正規化（最大値を 100）
peak = max(raw.values()) or 1.0
scores = {s: round(raw[s] / peak * 100, 1) for s in STYLES}

primary = max(scores, key=scores.get)
ranked = sorted(scores.items(), key=lambda x: -x[1])
secondary = ranked[1][0]
margin = scores[primary] - scores[secondary]
confidence = min(100.0, margin * 2.5)  # margin 40pt → confidence 100
```

### 5.2 判定ルール

| ルール | 内容 |
|--------|------|
| **Primary** | 正規化スコア最大の `name`（KG と同じ英語 key） |
| **Secondary** | 2 位のスタイル（UI で「〇〇の傾向もあります」） |
| **Confidence** | `primary_score - secondary_score` から算出（0–100%） |
| **低信頼** | confidence < 30% → 表示は「**混合型**（主: 〇〇 / 副: △△）」 |
| **Delegator ガード** | 次の **いずれかを満たさない** 場合、Delegator を 2 位以下に落とす:<br>① q6=`ask_others` OR q7=`people_pick`<br>② q5=`ai_decide` かつ q7=`shortlist` |
| **Impulsive ガード** | q6=`quick_deal` なしで Impulsive が 1 位 → 1 位を 2 位に降格し、q6 の加点最大スタイルを繰り上げ（衝動の単独誤判定防止） |

### 5.3 タイブレーク（同点時）

優先順位（設問の信頼度順）:

1. q6_decision_process の加点
2. q7_info_preference の加点
3. 母集団事前分布（稀な Delegator を下げ、Intuitive / Maximizer をやや優先は **しない** — 偏り防止のため **q6 の選択肢 key の辞書順ではなく、明示的な tie_break_order リスト**を使う）

```text
tie_break_order:
  Maximizer > Satisficer > Authority-driven > Intuitive > Impulsive > Delegator
```

※ 同点は稀。主に q6/q7 未回答のフォールバック用。

### 5.4 出力スキーマ（セッション `profile` 拡張）

```json
{
  "profile": { "score_safety": 80, "...": "..." },
  "decision_style": "Maximizer",
  "decision_style_label": "徹底比較型",
  "decision_style_description": "複数モデルを徹底的に比較・スペック重視",
  "decision_style_scores": {
    "Maximizer": 100,
    "Satisficer": 62,
    "Authority-driven": 58,
    "Delegator": 12,
    "Intuitive": 45,
    "Impulsive": 30
  },
  "decision_style_confidence": 72,
  "decision_style_secondary": "Authority-driven"
}
```

`decision_style_label` / `description` は `DECISION_STYLE_MASTER`（または API 側マスタ）から解決。

---

## 6. 設問とスタイルの対応マトリクス（一覧）

| スタイル | q6（主） | q7（主） | 既存補正 |
|----------|----------|----------|----------|
| Maximizer | compare_many | spec_table | q3 feature_lack, q4 too_much_info(弱), q5 ai_candidates |
| Satisficer | good_enough | shortlist | q3 unused, q4 too_much_info, q5 ai_decide |
| Authority-driven | trust_expert | awards_expert | q4 difficult_operation, q5 ai_candidates |
| Delegator | ask_others | people_pick | q5 ai_decide（**ガード必須**） |
| Intuitive | first_feeling | experience | q3 boredom, q5 self_decide |
| Impulsive | quick_deal | offer_now | q3 boredom, q5 self_decide（**ガード必須**） |

---

## 7. システム統合

### 7.1 変更ファイル（実装時）

| ファイル | 変更内容 |
|----------|----------|
| `config/questions.json` | q5 追加、q6・q7 追加（index 5–7） |
| `config/decision-style-weights.json` | **新規** — 回答 key → 6 スタイル配点 |
| `engine/demo_profile.py` | `compute_decision_style(answers)` 追加、`compute_from_answers` から呼出 |
| `api/demo/router.py` | `/answers` レスポンスに decision_style 系フィールド追加 |
| `demo-web` Questions UI | 7 問表示、結果 MAP にスタイル表示 |
| `api/demo/recommend_service.py` | `_archetype_for_rank` を **decision_style ベース** に差し替え（順位固定ラベルを廃止） |
| `api/demo/explainability.py` | Reason Trace に「あなたの決め方: 徹底比較型」ステップ追加 |

### 7.2 推薦エンジンとの接続

```cypher
// ユーザーの decision_style に訴求する Capability をブースト
MATCH (cap:Capability)-[:APPEALS_TO]->(ds:DecisionStyle {name: $user_style})
MATCH (v:VehicleModel)-[:HAS_FEATURE]->(tf:TechnicalFeature)-[:REALIZES]->(cap)
RETURN v.name, count(DISTINCT cap) AS appeal_score
```

- スコア補正: `final_score += appeal_bonus`（上限 +5〜10% 程度）
- 説明文: `information_preference` に沿ったトーン（比較表 vs ストーリー）

### 7.3 既存「アーキタイプ」ラベルとの関係

| 項目 | 現状 | 変更後 |
|------|------|--------|
| 車種カードの「安心重視型」等 | 順位で固定付与 | **廃止**し、ユーザー `decision_style_label` を共通表示、または車種別は KG の購入者分布 |
| 価値観 5 軸 | 維持 | 維持（別軸） |

---

## 8. 検証計画

### 8.1 単体テスト

- 各 q6 選択肢単独 → 対応スタイルが 1 位になること
- Delegator / Impulsive ガードが機能すること
- 全回答なし → `Satisficer` または confidence 0 のフォールバック

### 8.2 KG との整合（オフライン）

1. `consumer_decisions.json` の `decision_style`（LLM 付与）を正解ラベルとする
2. Quick Questions **に相当するプロキシ回答は存在しない**ため、次のいずれかで検証:
   - **A**: 小規模ユーザーテスト（10–20 名）で自己評価 vs 判定の一致率
   - **B**: 購入ストーリーから「プロセス設問」に相当する文をルール抽出し、擬似回答でバックテスト
3. 目標指標（初期）:
   - Top-1 一致率 **≥ 55%**（6 クラス・ランダム 17% 超）
   - Top-2 一致率 **≥ 80%**
   - Delegator の Precision **≥ 50%**（件数少のため Recall は参考）

### 8.3 デモ UX 検証

- 7 問完了率が 5 問時比 **-10% 以内**
- 「自分の決め方」表示後の納得感（定性 5 段階 ≥ 4）

---

## 9. 実装フェーズ

| Phase | 内容 | 成果物 |
|-------|------|--------|
| **P0** | 本計画レビュー・文言確定 | 承認済み `questions.json` 文案 |
| **P1** | `decision-style-weights.json` + `compute_decision_style` | 単体テスト |
| **P2** | API / セッション拡張、q5–q7 フロント | 7 問デモ動作 |
| **P3** | 推薦・explainability 連携 | KG 訴求ボーナス・Reason Trace |
| **P4** | ユーザーテスト・重み調整 | weights v1.1 |

---

## 10. リスクと対策

| リスク | 対策 |
|--------|------|
| 設問が増え離脱する | q6/q7 をコンパクトに。既存 MAP は q1–q4 まで更新し q5–q7 はバッチ更新でも可 |
| Delegator 過剰判定 | ガードルール + 稀少クラスは「委任の傾向」表現 |
| 自己申告と実行動のギャップ | confidence 表示・混合型ラベルで誠実に表現 |
| q5 が `questions.json` に未載 | P1 で q5 を追加（`score-weights.json` には既存） |

---

## 11. サンプル：回答パターンと期待判定

| パターン | q6 | q7 | q5 | 期待 Primary |
|--------|----|----|-----|----------------|
| A | compare_many | spec_table | ai_candidates | **Maximizer** |
| B | good_enough | shortlist | ai_decide | **Satisficer** |
| C | trust_expert | awards_expert | ai_candidates | **Authority-driven** |
| D | ask_others | people_pick | ai_decide | **Delegator** |
| E | first_feeling | experience | self_decide | **Intuitive** |
| F | quick_deal | offer_now | self_decide | **Impulsive** |

---

## 12. 関連ドキュメント

- [Quick Questions ロジック（現行）](./QUICK_QUESTIONS_LOGIC.md)
- [プロジェクトコンテキスト / DecisionStyle 定義](../CLAUDE.md)
- `graph/graph_builder.py` — `DECISION_STYLE_MASTER`
- `config/score-weights.json` — 価値観 5 軸（別系統）

---

**最終更新**: 2026-05-28  
**ステータス**: 計画（未実装）— レビュー後 P1 着手
