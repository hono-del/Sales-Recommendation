"""
Phase 2: Product feature structuring for knowledge graph

data/raw/products.json (product_scraper.py の出力) を読み込み、
グラフ構築用の Product Feature Schema に変換する。

PDFから抽出した場合もフォールバックデータの場合も同じ処理で対応。
LLMは必要最小限（target_needs の補完のみ）に留める。
"""
import json
import os
import re
from pathlib import Path

import anthropic

INPUT_PATH = Path("data/raw/products.json")
OUTPUT_PATH = Path("data/processed/product_features.json")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

VALID_NEEDS = {
    "safety", "space", "fuel_efficiency", "comfort",
    "design", "technology", "family", "offroad",
}

NEEDS_INFERENCE_PROMPT = """以下のLexus車種情報から、この車種が満たす顧客ニーズを推定してください。

車種: {model_name}
カテゴリ: {category}
特徴: {features}
安全機能: {safety_features}
技術装備: {technology}
定員: {seating_capacity}人
燃料: {fuel_type}

以下のニーズカテゴリから該当するものをすべて選んでJSON配列で返してください（3〜5個が目安）:
safety, space, fuel_efficiency, comfort, design, technology, family, offroad

JSONのみ返してください。例: ["safety", "space", "comfort"]"""


def infer_needs_with_llm(product: dict, client: anthropic.Anthropic) -> list[str]:
    """LLMで target_needs を推定する（既存データがない場合のフォールバック）。"""
    specs = product.get("specs", {})
    prompt = NEEDS_INFERENCE_PROMPT.format(
        model_name=product.get("model_name", ""),
        category=product.get("category", ""),
        features=", ".join(product.get("features", [])[:4]),
        safety_features=", ".join(product.get("safety_features", [])[:3]),
        technology=", ".join(product.get("technology", [])[:3]),
        seating_capacity=specs.get("seating_capacity", 5),
        fuel_type=specs.get("fuel_type", ""),
    )
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        needs = json.loads(raw)
        # バリデーション
        return [n for n in needs if n in VALID_NEEDS]
    except Exception as e:
        print(f"  [WARN] LLM needs inference failed: {e}")
        return _heuristic_needs(product)


def _heuristic_needs(product: dict) -> list[str]:
    """ルールベースでニーズを推定する（LLM不使用フォールバック）。"""
    needs = set()
    category = product.get("category", "")
    specs = product.get("specs", {})
    model = product.get("model_name", "").upper()
    features_text = " ".join(product.get("features", [])).lower()
    fuel = specs.get("fuel_type", "").lower()
    seats = specs.get("seating_capacity", 5)

    # カテゴリ別
    if category == "SUV":
        needs.add("safety")
        if seats >= 7:
            needs.update(["space", "family"])
    elif category == "SEDAN":
        needs.add("comfort")
    elif category == "MINIVAN":
        needs.update(["space", "family"])

    # 特徴テキスト解析
    if any(w in features_text for w in ["オフロード", "四輪", "悪路"]):
        needs.add("offroad")
    if any(w in features_text for w in ["先進", "技術", "デジタル", "電動"]):
        needs.add("technology")
    if any(w in features_text for w in ["デザイン", "スポーティ", "エレガント", "スタイル"]):
        needs.add("design")

    # 燃料
    if any(w in fuel for w in ["ハイブリッド", "電気", "phev", "ev"]):
        needs.add("fuel_efficiency")

    # 安全は常に追加
    needs.add("safety")

    return list(needs)


def normalize_product(product: dict, client: anthropic.Anthropic | None) -> dict:
    """
    raw product dict → processed product feature dict.
    target_needs が既にある場合はそのまま使用、なければ推定。
    """
    model_name = product.get("model_name", "Unknown")
    specs = product.get("specs", {})

    # target_needs の取得・推定
    existing_needs = [n for n in product.get("target_needs", []) if n in VALID_NEEDS]
    if existing_needs:
        satisfies_needs = existing_needs
    elif client:
        satisfies_needs = infer_needs_with_llm(product, client)
    else:
        satisfies_needs = _heuristic_needs(product)

    return {
        "model_name": model_name,
        "category": product.get("category", "SUV"),
        "features": product.get("features", []),
        "safety_features": product.get("safety_features", []),
        "technology": product.get("technology", []),
        "specs": {
            "price_range": specs.get("price_range", ""),
            "fuel_type": specs.get("fuel_type", ""),
            "seating_capacity": int(specs.get("seating_capacity", 5)),
        },
        "satisfies_needs": satisfies_needs,
    }


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    products = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    print(f"Processing {len(products)} products from {INPUT_PATH}")

    # target_needs がない製品のみLLMを使う
    needs_llm = any(not p.get("target_needs") for p in products)
    client = None
    if needs_llm:
        if not ANTHROPIC_API_KEY:
            print("[WARN] ANTHROPIC_API_KEY not set — using heuristic needs inference")
        else:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    features_list = []
    for i, product in enumerate(products):
        model_name = product.get("model_name", "?")
        source = "LLM" if (client and not product.get("target_needs")) else "pass-through"
        print(f"  [{i+1}/{len(products)}] {model_name:6s} ({source})")
        features = normalize_product(product, client)
        features_list.append(features)
        print(f"    needs: {features['satisfies_needs']}")

    OUTPUT_PATH.write_text(
        json.dumps(features_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved {len(features_list)} product features → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
