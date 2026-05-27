"""
rule_based_extractor.py
-----------------------
LLM を使わずキーワード・正規表現で consumer_decisions.json を生成する。

decision_style / regret は空値で出力し、
batch_llm_extractor.py で後から補完する。
"""
import json
import re
from collections import defaultdict
from pathlib import Path

INPUT_PATH  = Path("data/raw/consumer_stories.json")
OUTPUT_PATH = Path("data/processed/consumer_decisions.json")

# ── カテゴリマップ ─────────────────────────────────────────────────────────────

TRIGGER_KEYWORDS: dict[str, list[str]] = {
    "vehicle_aging":     ["老朽", "古くなり", "年数", "走行距離が", "ガタ", "ぼろ", "乗り換え時期", "10年", "15年", "20年"],
    "inspection":        ["車検", "しゃけん"],
    "accident":          ["事故", "故障", "廃車", "追突", "ぶつけ"],
    "maintenance_cost":  ["維持費", "修理代", "修理費", "燃料代が高", "ガソリン代が高"],
    "new_model_release": ["新型", "フルモデルチェンジ", "新発売", "モデルチェンジ"],
    "promotion":         ["キャンペーン", "値引き", "特価", "決算"],
    "test_drive":        ["試乗", "口コミ", "評判", "友人に勧め", "知人に勧め"],
    "lifestyle_change":  ["アウトドア", "趣味", "キャンプ", "ライフスタイル", "趣味が"],
}

LIFE_EVENT_KEYWORDS: dict[str, list[str]] = {
    "child_birth":    ["子供が生まれ", "赤ちゃん", "出産", "妊娠", "誕生", "子どもが生まれ"],
    "marriage":       ["結婚", "婚約", "入籍", "新婚"],
    "relocation":     ["引越", "引っ越し", "転勤", "転居", "移住"],
    "job_change":     ["転職", "就職", "独立開業", "新しい職場"],
    "retirement":     ["定年", "退職", "リタイア"],
    "child_school":   ["入学", "進学", "通学", "幼稚園", "小学校", "中学校", "高校", "大学"],
    "home_purchase":  ["マイホーム", "一軒家", "新築", "家を買", "土地を買"],
    "independence":   ["一人暮らし", "独立", "実家を出"],
    "family_growth":  ["家族が増え", "2人目", "3人目", "兄弟"],
}

NEED_KEYWORDS: dict[str, list[str]] = {
    "safety":          ["安全", "セーフティ", "Honda SENSING", "衝突", "エアバッグ", "ADAS"],
    "space":           ["広", "収納", "荷室", "積載", "スペース", "大きい車内", "ラゲッジ"],
    "fuel_efficiency": ["燃費", "低燃費", "エコ", "ハイブリッド", "電費", "ガソリン代"],
    "comfort":         ["乗り心地", "快適", "静粛", "静か", "振動が少"],
    "design":          ["デザイン", "スタイル", "カッコ", "おしゃれ", "見た目", "外観"],
    "technology":      ["ナビ", "オーディオ", "コネクト", "先進", "テクノロジー", "デジタル"],
    "family":          ["家族", "チャイルドシート", "子供", "みんなで", "ファミリー"],
    "offroad":         ["4WD", "オフロード", "悪路", "雪道", "AWD", "四駆"],
}

USAGE_KEYWORDS: dict[str, list[str]] = {
    "family_use":  ["家族", "子供", "ファミリー", "送り迎え", "買い物"],
    "commute":     ["通勤", "通学", "毎日乗る", "日常の足"],
    "business":    ["営業", "仕事", "業務", "取引先"],
    "outdoor":     ["アウトドア", "キャンプ", "登山", "釣り", "スキー"],
    "leisure":     ["ドライブ", "旅行", "週末", "レジャー"],
}

MARITAL_KEYWORDS = {
    "married": ["妻", "夫", "配偶者", "奥さん", "旦那", "嫁", "主人", "夫婦", "パートナー", "婚"],
    "single":  ["独身", "一人暮らし", "彼女いない", "彼氏いない", "未婚"],
}

HOUSEHOLD_KEYWORDS = {
    "single":   ["一人暮らし", "独身"],
    "couple":   ["夫婦二人", "2人暮らし", "夫婦のみ", "二人きり"],
    "nuclear":  ["子供と", "子どもと", "家族4人", "家族3人", "家族5人", "3人家族", "4人家族"],
    "extended": ["両親と同居", "親と同居", "祖父母と", "義父", "義母", "実家に"],
}

CHILDREN_AGE_KEYWORDS = {
    "infant":       ["乳児", "赤ちゃん", "0歳", "1歳", "2歳", "3歳", "4歳", "5歳", "乳幼児", "未就学"],
    "elementary":   ["小学生", "小学校", "6歳", "7歳", "8歳", "9歳", "10歳", "11歳", "12歳"],
    "middle_high":  ["中学生", "高校生", "中高生", "13歳", "14歳", "15歳", "16歳", "17歳", "18歳"],
    "adult":        ["大学生", "社会人の子", "成人した子", "子供が独立"],
}

ELDERLY_KEYWORDS = ["両親", "父母", "祖父", "祖母", "おじいちゃん", "おばあちゃん",
                    "高齢", "介護", "シニア", "親の送迎"]

# Honda グレード正規表現
GRADE_PATTERN = re.compile(
    r'\b(RS|G|EX|L|Z|Absolute|absolute|モデューロX|Modulo X|'
    r'Honda SENSING|SENSING|αパッケージ|Gパッケージ|Lパッケージ|'
    r'ブラックエディション|スパーダ|SPADA|MUGEN|無限|TYPE R|Type R|'
    r'e:HEV|e:PHEV|1\.5L|2\.0L|1\.5T|RS\+|G・EX|Lターボ)\b'
)

# 色パターン（主要なもの）
COLOR_PATTERN = re.compile(
    r'(プレミアム\w+メタリック|プレミアム\w+パール|'
    r'クリスタル\w+|シャイニング\w+|'
    r'ルーナ\w+メタリック|'
    r'プラチナ\w+|'
    r'ミッドナイトブルービーム|'
    r'ソニックグレー|ソニックシルバー|'
    r'チャンピオンシップホワイト|'
    r'ボールドベージュ|'
    r'(白|黒|赤|青|緑|銀|灰|茶|金|ベージュ|シルバー|ホワイト|ブラック|レッド|ブルー|グリーン|グレー|ゴールド)'
    r'(\w*(メタリック|パール|マイカ|ソリッド))?)'
)

# オプション装備キーワード
OPTION_KEYWORDS = [
    "純正ナビ", "メモリーナビ", "ナビゲーション", "カーナビ",
    "ETC", "ETC2.0",
    "バックカメラ", "バックモニター", "リアカメラ",
    "ドライブレコーダー", "ドラレコ",
    "サンルーフ", "パノラマルーフ", "ムーンルーフ",
    "Honda SENSING", "SENSING",
    "コーナーセンサー", "パーキングセンサー",
    "シートヒーター", "ヒーテッドシート",
    "電動シート", "パワーシート",
    "電動スライドドア", "パワースライドドア",
    "LEDヘッドライト", "フォグランプ",
    "スマートキー", "キーレス",
    "ワンセグ", "フルセグ",
    "クルーズコントロール", "アダプティブクルーズ",
    "アルミホイール",
]

# Honda 競合・前所有車検出パターン
CAR_MODEL_PATTERN = re.compile(
    r'(アルファード|ヴェルファイア|プリウス|カローラ|ヤリス|RAV4|ハリアー|'
    r'セレナ|ノア|ヴォクシー|エルグランド|ステップワゴン|フリード|'
    r'マツダ\w+|CX-\d|アテンザ|デミオ|'
    r'フォレスター|アウトバック|レヴォーグ|インプレッサ|'
    r'エクストレイル|ジューク|リーフ|'
    r'スイフト|ジムニー|ソリオ|エブリイ|'
    r'前の車|以前の車|乗り換え前)'
)


# ── ユーティリティ ────────────────────────────────────────────────────────────

def _full_text(story: dict) -> str:
    st = story.get("story_text", {})
    if isinstance(st, dict):
        parts = [
            story.get("kikkake", ""),
            story.get("most_satisfied", ""),
            st.get("purchase_trigger", ""),
            st.get("purchase_story", ""),
            st.get("deciding_factor", ""),
            st.get("advice", ""),
        ]
    else:
        parts = [story.get("kikkake", ""), story.get("most_satisfied", ""), str(st)]
    return " ".join(p for p in parts if p)


def _match_first(text: str, keyword_map: dict[str, list[str]]) -> str | None:
    for key, keywords in keyword_map.items():
        if any(kw in text for kw in keywords):
            return key
    return None


def _match_all(text: str, keyword_map: dict[str, list[str]]) -> list[str]:
    return [key for key, kws in keyword_map.items() if any(kw in text for kw in kws)]


def _extract_family_size(text: str) -> int | None:
    m = re.search(r'([2-8])人家族', text)
    if m:
        return int(m.group(1))
    m = re.search(r'家族([2-8])人', text)
    if m:
        return int(m.group(1))
    return None


def _extract_children_count(text: str) -> int:
    # 明示的な人数
    m = re.search(r'子供([1-4])人|子ども([1-4])人|([1-4])人の子', text)
    if m:
        return int(next(g for g in m.groups() if g))
    # 「長男・次男」等
    count = 0
    for word in ["長男", "長女", "次男", "次女", "三男", "三女"]:
        if word in text:
            count += 1
    return count if count else (1 if any(w in text for w in ["子供", "子ども", "息子", "娘"]) else 0)


def _extract_purchase_year(story: dict) -> int | None:
    post_date = story.get("post_date", "")
    if post_date and len(str(post_date)) >= 4:
        try:
            return int(str(post_date)[:4])
        except ValueError:
            pass
    return None


def _extract_grade(text: str) -> str | None:
    m = GRADE_PATTERN.search(text)
    return m.group(0) if m else None


def _extract_color(text: str) -> str | None:
    m = COLOR_PATTERN.search(text)
    return m.group(0) if m else None


def _extract_options(text: str) -> list[str]:
    return [opt for opt in OPTION_KEYWORDS if opt in text]


def _extract_evaluation_criteria(text: str, needs: list[str]) -> list[str]:
    """needs から代表的な評価基準を生成（ルールベース）。"""
    mapping = {
        "safety":          "安全性能",
        "space":           "室内の広さ・収納",
        "fuel_efficiency": "燃費・経済性",
        "comfort":         "乗り心地・快適性",
        "design":          "デザイン・スタイル",
        "technology":      "先進技術・装備",
        "family":          "家族向け機能",
        "offroad":         "走破性・悪路性能",
    }
    criteria = [mapping[n] for n in needs if n in mapping]
    # 価格は常に追加
    if "価格" not in criteria and ("値段" in text or "価格" in text or "予算" in text):
        criteria.append("価格・コストパフォーマンス")
    return criteria[:4]  # 最大4つ


def _extract_purchase_driver(story: dict) -> str:
    st = story.get("story_text", {})
    if isinstance(st, dict):
        deciding = st.get("deciding_factor", "")
        if deciding and len(deciding) > 5:
            return deciding[:50]
    most_sat = story.get("most_satisfied", "")
    if most_sat:
        return most_sat[:50]
    return "総合的な満足度"


def _extract_considered_options(text: str, selected: str) -> list[str]:
    options = [selected]
    for m in CAR_MODEL_PATTERN.finditer(text):
        name = m.group(0)
        if name not in options and len(name) < 20:
            options.append(name)
    return options[:5]


# ── メイン抽出関数 ────────────────────────────────────────────────────────────

def extract_decision_rules(story: dict) -> dict:
    text    = _full_text(story)
    kikkake = story.get("kikkake", "")
    model   = story.get("vehicle_model", "Unknown")
    score   = story.get("satisfaction_score")

    # --- Trigger ---
    trigger = _match_first(kikkake + " " + text, TRIGGER_KEYWORDS) or "other"

    # --- LifeEvent ---
    life_event = _match_first(text, LIFE_EVENT_KEYWORDS)

    # --- Needs ---
    needs = _match_all(text, NEED_KEYWORDS) or ["safety", "comfort"]

    # --- Usage ---
    usage = _match_first(text, USAGE_KEYWORDS) or "family_use"

    # --- Annual mileage ---
    mileage = "unknown"
    m = re.search(r'(\d+)[,，]?(\d*)[\s]*[万]?[kK][mM]', text)
    if m:
        km = int(m.group(1).replace(",", "")) * (10000 if "万" in text[max(0, m.start()-1):m.start()+3] else 1)
        if km < 5000:
            mileage = "low(<5000km)"
        elif km <= 15000:
            mileage = "medium(5000-15000km)"
        else:
            mileage = "high(>15000km)"

    # --- Family composition ---
    family_size    = _extract_family_size(text)
    children_count = _extract_children_count(text)
    children_ages  = _match_all(text, CHILDREN_AGE_KEYWORDS)
    marital_status = _match_first(text, MARITAL_KEYWORDS) or "unknown"
    household_type = _match_first(text, HOUSEHOLD_KEYWORDS) or "unknown"
    has_elderly    = True if any(kw in text for kw in ELDERLY_KEYWORDS) else (None if "親" not in text else False)

    # family_size の補完
    if not family_size and children_count > 0:
        family_size = 2 + children_count  # 親2 + 子供
    elif not family_size and marital_status == "married":
        family_size = 2

    # --- Vehicle details ---
    grade          = _extract_grade(text)
    body_color     = _extract_color(text)
    options        = _extract_options(text)
    purchase_year  = _extract_purchase_year(story)

    # --- EvaluationCriteria / PurchaseDriver ---
    eval_criteria  = _extract_evaluation_criteria(text, needs)
    purchase_driver = _extract_purchase_driver(story)

    # --- Considered options ---
    considered = _extract_considered_options(text, model)

    # --- Outcome ---
    outcome = story.get("most_satisfied", "") or f"満足度{score}/5"

    return {
        "story_id":   story["story_id"],
        "title":      story.get("title", ""),
        "gender":     story.get("gender", ""),
        "age_group":  story.get("age_group", ""),
        "location":   story.get("location", ""),
        "post_date":  story.get("post_date", ""),
        "satisfaction_score": score,

        "consumer_context": {
            "family_size":    family_size,
            "children":       children_count,
            "children_ages":  children_ages,
            "marital_status": marital_status,
            "household_type": household_type,
            "has_elderly":    has_elderly,
            "usage":          usage,
            "annual_mileage": mileage,
        },

        "life_event":  life_event,
        "trigger":     trigger,

        # decision_style / regret は batch_llm_extractor で補完
        "decision_style": None,
        "regret":         [],

        "needs":               needs,
        "evaluation_criteria": eval_criteria,
        "purchase_driver":     purchase_driver,
        "considered_options":  considered,
        "selected_vehicle":    model,

        "vehicle_details": {
            "brand":              "Honda",
            "grade":              grade,
            "model_year":         None,
            "body_color":         body_color,
            "interior_color":     None,
            "optional_equipment": options,
        },

        "previous_vehicle": None,
        "purchase_year":    purchase_year,
        "outcome":          outcome[:100],
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_stories = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(all_stories)} stories")

    decisions = []
    for i, story in enumerate(all_stories):
        d = extract_decision_rules(story)
        decisions.append(d)
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(all_stories)}] 処理中...")

    OUTPUT_PATH.write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(decisions)} decisions -> {OUTPUT_PATH}")
    print("次のステップ: python extractor/batch_llm_extractor.py")


if __name__ == "__main__":
    main()
