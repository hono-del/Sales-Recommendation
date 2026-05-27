"""
Phase 2 (v2): LLM-based consumer decision structuring — extended ontology

Honda購入ストーリーから以下を抽出:
  - DecisionStyle (Maximizer/Satisficer/Authority-driven/Delegator/Intuitive/Impulsive)
  - LifeEvent  (購入背景のライフイベント: child_birth / marriage / relocation 等)
  - Trigger    (直接の購入きっかけ: vehicle_aging / inspection / new_model 等)
  - Needs / EvaluationCriteria / PurchaseDriver (既存)
  - Regret     (後悔・不満: 満足度 1-3 のストーリーから主に抽出)
  - VehicleOwnership (前所有車・購入年等、読み取れる場合のみ)
"""
import json
import os
import random
import re
import time
from collections import defaultdict
from pathlib import Path

import anthropic

INPUT_PATH  = Path("data/raw/consumer_stories.json")
OUTPUT_PATH = Path("data/processed/consumer_decisions.json")

SAMPLE_SIZE = int(os.environ.get("CONSUMER_SAMPLE_SIZE", "300"))
REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "0"))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """あなたは消費者の購買意思決定を分析する専門家です。
与えられた自動車購入ストーリーを読み、以下のJSON形式で構造化してください。
必ず有効なJSONのみを返してください。説明文は不要です。"""

EXTRACTION_PROMPT = """以下の自動車購入ストーリーを分析し、指定のJSON形式で出力してください。

--- 基本情報 ---
車種: {vehicle_model}
購入のきっかけ（kikkake）: {kikkake}
最も満足した点: {most_satisfied}
満足度: {satisfaction_score}/5

--- ストーリー ---
購入のきっかけ（詳細）: {purchase_trigger}
購入のストーリー: {purchase_story}
決め手: {deciding_factor}
アドバイス: {advice}

出力形式（JSONのみ・コードブロック不要）:
{{
  "consumer_context": {{
    "family_size": <推定家族人数（整数、不明なら null）>,
    "children": <推定子供人数（整数、不明なら 0）>,
    "children_ages": [
      "<子供の年齢層（複数可）: infant=乳幼児(0-5歳) | elementary=小学生(6-12歳) | middle_high=中高生(13-18歳) | adult=成人(19歳以上)>"
    ],
    "marital_status": "<婚姻状況: married=既婚 | single=未婚・独身 | unknown>",
    "household_type": "<世帯構成: single=一人暮らし | couple=夫婦のみ | nuclear=夫婦＋子供 | extended=親/祖父母と同居 | unknown>",
    "has_elderly": <高齢家族との同居: true | false | null（不明）>,
    "usage": "<主な使用用途: family_use | commute | business | outdoor | leisure>",
    "annual_mileage": "<推定年間走行距離: low(<5000km) | medium(5000-15000km) | high(>15000km) | unknown>"
  }},

  "life_event": "<購入の背景となったライフイベント（長期的な生活変化）。以下から最も当てはまるものを1つ選ぶ。なければ null。
    child_birth=子供誕生, marriage=結婚, relocation=引越し・転勤, job_change=転職・就職,
    retirement=定年退職, child_school=子供の入学・進学, home_purchase=マイホーム購入,
    independence=独立・一人暮らし, family_growth=家族が増えた（その他）>",

  "trigger": "<直接の購入検討きっかけ（車に関わる直接的な事象）。以下から最も当てはまるものを1つ選ぶ。
    vehicle_aging=車の老朽化・経年劣化, inspection=車検, accident=事故・故障,
    maintenance_cost=維持費増加, new_model_release=新型モデル発売, promotion=キャンペーン・値引き,
    test_drive=試乗・口コミ, lifestyle_change=ライフスタイル変化（趣味・アウトドア等）,
    other=その他>",

  "decision_style": "<意思決定スタイル。以下から1つ選ぶ。
    Maximizer=徹底比較型（複数モデルを詳細に比較・スペック重視）,
    Satisficer=十分型（一定基準を満たしたら決定）,
    Authority-driven=権威依存型（営業・家族・友人・ブランドの意見に従う）,
    Delegator=委任型（意思決定を他者に委ねる）,
    Intuitive=直感型（フィーリング・一目惚れ）,
    Impulsive=衝動型（勢い・その場で即決）>",

  "needs": [
    "<ニーズ: safety | space | fuel_efficiency | comfort | design | technology | family | offroad から3つまで選択>"
  ],

  "evaluation_criteria": [
    "<評価基準1（例: 安全性能, 燃費, 価格, デザイン, 信頼性）>",
    "<評価基準2>"
  ],

  "purchase_driver": "<最終的な決め手（1フレーズ）>",

  "considered_options": [
    "<検討した車種（不明なら選択車種のみ）>"
  ],

  "selected_vehicle": "<最終的に選んだ車種（Hondaモデル名）>",

  "vehicle_details": {{
    "brand": "<購入車のブランド名: Honda | Toyota | Nissan | Mazda | Subaru | Daihatsu | Suzuki | Mitsubishi | Lexus | other>",
    "grade": "<グレード/トリム（例: RS, G, EX, L, Honda SENSING, Z, Absolute, Modulo X, αパッケージ）。読み取れる場合のみ。不明なら null>",
    "model_year": <車の年式・モデルイヤー（西暦整数。例: 2023）。読み取れる場合のみ。不明なら null>,
    "body_color": "<ボディカラー（例: プレミアムクリスタルレッド・メタリック、パールホワイト）。不明なら null>",
    "interior_color": "<インテリアカラー（例: ブラック、アイボリー）。不明なら null>",
    "optional_equipment": [
      "<オプション装備（例: 純正ナビ, ETC, バックカメラ, サンルーフ, Honda SENSING, ドラレコ）>"
    ]
  }},

  "previous_vehicle": "<前所有車（読み取れる場合のみ。不明なら null）>",

  "purchase_year": <購入年（読み取れる場合のみ整数。不明なら null）>,

  "outcome": "<購入後の結果・満足度（1文）>",

  "regret": [
    {{
      "category": "<後悔カテゴリ: fuel_cost | cargo_space | ride_quality | size_too_large | size_too_small | price | maintenance | design | technology | other>",
      "description": "<後悔の内容（1文）>",
      "severity": <深刻度 1-3（1=軽微, 2=中程度, 3=重大）>
    }}
  ]
}}

注意:
- regret は満足度が低い場合（1-3点）や不満・後悔の表現がある場合に記入。なければ空配列 []。
- life_event と trigger は別物。life_event=長期的な生活変化、trigger=車購入の直接きっかけ。
- 両方該当する場合はそれぞれ記入（例: life_event=child_birth, trigger=vehicle_aging）。
- vehicle_details の optional_equipment はストーリーに明示されている装備のみ記入。なければ空配列 []。
- vehicle_details の各フィールドは読み取れる場合のみ記入し、不明な場合は null または空配列。"""


def story_text_to_str(story_text) -> dict[str, str]:
    """story_text が dict でも str でも 4フィールドのdictに正規化する。"""
    if isinstance(story_text, dict):
        return {
            "purchase_trigger": story_text.get("purchase_trigger", ""),
            "purchase_story":   story_text.get("purchase_story", ""),
            "deciding_factor":  story_text.get("deciding_factor", ""),
            "advice":           story_text.get("advice", ""),
        }
    text = str(story_text)
    return {
        "purchase_trigger": text[:400],
        "purchase_story":   text[400:800],
        "deciding_factor":  text[800:1100],
        "advice":           text[1100:1400],
    }


def stratified_sample(stories: list[dict], total: int) -> list[dict]:
    """車種別に均等になるよう層別サンプリングを行う。"""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for s in stories:
        model = s.get("vehicle_model", "Unknown")
        by_model[model].append(s)

    models = list(by_model.keys())
    per_model = max(1, total // len(models))
    sampled = []

    for model, items in by_model.items():
        random.shuffle(items)
        sampled.extend(items[:per_model])

    random.shuffle(sampled)
    if len(sampled) < total:
        remaining = [s for s in stories if s not in sampled]
        random.shuffle(remaining)
        sampled.extend(remaining[: total - len(sampled)])

    return sampled[:total]


def extract_decision(story: dict, client: anthropic.Anthropic) -> dict | None:
    texts = story_text_to_str(story.get("story_text", {}))

    prompt = EXTRACTION_PROMPT.format(
        vehicle_model    = story.get("vehicle_model", "不明"),
        kikkake          = story.get("kikkake", "不明"),
        most_satisfied   = story.get("most_satisfied", "不明"),
        satisfaction_score = story.get("satisfaction_score", "不明"),
        purchase_trigger = texts["purchase_trigger"][:400],
        purchase_story   = texts["purchase_story"][:500],
        deciding_factor  = texts["deciding_factor"][:300],
        advice           = texts["advice"][:200],
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        decision = json.loads(raw)
        decision["story_id"]  = story["story_id"]
        decision["title"]     = story.get("title", "")
        decision["gender"]    = story.get("gender", "")
        decision["age_group"] = story.get("age_group", "")
        decision["location"]  = story.get("location", "")
        decision["post_date"] = story.get("post_date", "")
        decision["satisfaction_score"] = story.get("satisfaction_score")
        # selected_vehicle がなければスクレイプ済み車種で補完
        if not decision.get("selected_vehicle"):
            decision["selected_vehicle"] = story.get("vehicle_model", "Unknown")
        # vehicle_details が存在しない場合はデフォルト値
        if "vehicle_details" not in decision:
            decision["vehicle_details"] = {
                "brand": "Honda",
                "grade": None,
                "model_year": None,
                "body_color": None,
                "interior_color": None,
                "optional_equipment": [],
            }
        else:
            vd = decision["vehicle_details"]
            vd.setdefault("brand", "Honda")
            vd.setdefault("grade", None)
            vd.setdefault("model_year", None)
            vd.setdefault("body_color", None)
            vd.setdefault("interior_color", None)
            vd.setdefault("optional_equipment", [])
        # regret が存在しない場合は空リストに
        if "regret" not in decision:
            decision["regret"] = []
        return decision
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse error for {story['story_id']}: {e}")
        return _fallback_decision(story)
    except Exception as e:
        print(f"  [WARN] LLM error for {story['story_id']}: {e}")
        return _fallback_decision(story)


def _fallback_decision(story: dict) -> dict:
    """LLM が失敗した場合の最小構造。"""
    model   = story.get("vehicle_model", "Unknown")
    kikkake = story.get("kikkake", "")
    needs   = ["safety", "space", "fuel_efficiency"]
    if "安全" in kikkake:
        needs = ["safety", "comfort"]
    elif "燃費" in kikkake:
        needs = ["fuel_efficiency", "comfort"]
    elif "家族" in kikkake or "子供" in kikkake:
        needs = ["family", "space", "safety"]

    return {
        "story_id":   story["story_id"],
        "title":      story.get("title", ""),
        "gender":     story.get("gender", ""),
        "age_group":  story.get("age_group", ""),
        "location":   story.get("location", ""),
        "post_date":  story.get("post_date", ""),
        "satisfaction_score": story.get("satisfaction_score"),
        "consumer_context": {
            "family_size":    None,
            "children":       0,
            "children_ages":  [],
            "marital_status": "unknown",
            "household_type": "unknown",
            "has_elderly":    None,
            "usage":          "family_use",
            "annual_mileage": "unknown",
        },
        "life_event":      None,
        "trigger":         "vehicle_aging",
        "decision_style":  "Satisficer",
        "needs":           needs,
        "evaluation_criteria": ["安全性", "燃費", "価格"],
        "purchase_driver": "総合的な満足度",
        "considered_options": [model],
        "selected_vehicle":   model,
        "vehicle_details": {
            "brand": "Honda",
            "grade": None,
            "model_year": None,
            "body_color": None,
            "interior_color": None,
            "optional_equipment": [],
        },
        "previous_vehicle":   None,
        "purchase_year":      None,
        "outcome":  f"満足度{story.get('satisfaction_score', 3)}/5",
        "regret":   [],
    }


def _safe_print(*args, **kwargs):
    """CP932 で表現できない文字を含む場合も安全に print する。"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe = " ".join(str(a).encode("cp932", errors="replace").decode("cp932") for a in args)
        print(safe, **{k: v for k, v in kwargs.items() if k != "end"})


def main():
    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY not set")
        raise SystemExit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_stories = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(all_stories)} stories from {INPUT_PATH}")

    random.seed(42)
    stories = stratified_sample(all_stories, SAMPLE_SIZE)
    print(f"Sampled {len(stories)} stories (stratified by vehicle model)")

    # --- レジューム: 既存の処理済み story_id をスキップ ---
    done_ids: set[str] = set()
    decisions: list[dict] = []
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            decisions = existing
            done_ids  = {d["story_id"] for d in existing}
            print(f"  [RESUME] {len(done_ids)} 件処理済み・スキップします")
        except Exception:
            pass

    model_counts: dict[str, int] = defaultdict(int)
    for s in stories:
        model_counts[s.get("vehicle_model", "Unknown")] += 1
    for model, cnt in sorted(model_counts.items(), key=lambda x: -x[1]):
        print(f"  {model:20s}: {cnt}")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    pending = [s for s in stories if s["story_id"] not in done_ids]
    print(f"  処理対象: {len(pending)} 件（残り）")

    first = True
    for i, story in enumerate(pending):
        sid   = story["story_id"]
        title = story.get("title", "")[:35]
        _safe_print(f"  [{len(done_ids)+i+1}/{len(stories)}] {sid}: {title}", flush=True)
        if REQUEST_DELAY > 0 and not first:
            time.sleep(REQUEST_DELAY)
        first = False
        decision = extract_decision(story, client)
        if decision:
            decisions.append(decision)
        # 100件ごとに中間保存
        if (i + 1) % 100 == 0:
            OUTPUT_PATH.write_text(
                json.dumps(decisions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  [CHECKPOINT] 累計 {len(decisions)} 件保存済み", flush=True)

    OUTPUT_PATH.write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved {len(decisions)} decisions -> {OUTPUT_PATH}")
    print(f"Tip: CONSUMER_SAMPLE_SIZE 環境変数で件数を変更できます（現在: {SAMPLE_SIZE}）")


if __name__ == "__main__":
    main()
