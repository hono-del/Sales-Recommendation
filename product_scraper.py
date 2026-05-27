"""
Phase 1: Lexus product information extractor
PDFカタログ or フォールバックデータから車種情報を取得する。

PDF配置場所:
  data/raw/lexus_catalogs/<MODEL>/*.pdf   ← サブフォルダ方式（推奨）
  data/raw/lexus_catalogs/*.pdf           ← フラット方式（後方互換）

  例:
    data/raw/lexus_catalogs/RZ/specificationslist.pdf
    data/raw/lexus_catalogs/RZ/pricelist.pdf
    data/raw/lexus_catalogs/LX/specificationslist.pdf

各モデルフォルダ内で使用するPDF優先順位:
  specificationslist > pricelist > equipmentlist > styles > selections > dealer_option > *_catalog

PDFが存在する場合は Claude API (claude-opus-4-5) でテキスト抽出、
なければ内蔵フォールバックデータを使用。
"""
import base64
import json
import os
import re
import time
from pathlib import Path

import anthropic

OUTPUT_PATH = Path("data/raw/products.json")
PDF_DIR = Path("data/raw/lexus_catalogs")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Fallback product data (used when no PDFs are found) ───────────────────────
FALLBACK_PRODUCTS: list[dict] = [
    {
        "model_name": "LX",
        "category": "SUV",
        "features": ["本格四輪駆動", "3列シート", "豪華内装", "最上級フラッグシップSUV"],
        "safety_features": ["レクサスセーフティシステム+", "プリクラッシュセーフティ", "レーンディパーチャーアラート"],
        "technology": ["マルチメディア14インチ画面", "Mark Levinson サラウンドサウンド", "ヘッドアップディスプレイ"],
        "specs": {
            "price_range": "17,000,000〜21,000,000円",
            "fuel_type": "ガソリン",
            "seating_capacity": 7,
        },
        "target_needs": ["space", "safety", "offroad", "comfort"],
    },
    {
        "model_name": "GX",
        "category": "SUV",
        "features": ["本格オフロード性能", "3列シート", "ラダーフレーム構造", "タフ＆プレミアム"],
        "safety_features": ["レクサスセーフティシステム+", "マルチテレインモニター"],
        "technology": ["14インチマルチメディア", "ワイヤレス充電", "先進運転支援"],
        "specs": {
            "price_range": "9,500,000〜13,000,000円",
            "fuel_type": "ガソリン",
            "seating_capacity": 7,
        },
        "target_needs": ["space", "safety", "offroad", "family"],
    },
    {
        "model_name": "RX",
        "category": "SUV",
        "features": ["ミッドサイズSUV", "洗練されたデザイン", "ハイブリッド設定あり", "快適な乗り心地"],
        "safety_features": ["レクサスセーフティシステム+", "プリクラッシュセーフティ", "レーダークルーズコントロール"],
        "technology": ["14インチタッチスクリーン", "Apple CarPlay/Android Auto", "ヘッドアップディスプレイ"],
        "specs": {
            "price_range": "6,500,000〜10,000,000円",
            "fuel_type": "ハイブリッド/ガソリン",
            "seating_capacity": 5,
        },
        "target_needs": ["safety", "comfort", "fuel_efficiency", "design"],
    },
    {
        "model_name": "NX",
        "category": "SUV",
        "features": ["コンパクトSUV", "PHEVモデルあり", "都市型SUV", "スポーティデザイン"],
        "safety_features": ["レクサスセーフティシステム+", "パーキングサポートブレーキ"],
        "technology": ["14インチインフォテインメント", "ワイヤレス充電", "デジタルアウターミラー"],
        "specs": {
            "price_range": "5,000,000〜7,500,000円",
            "fuel_type": "ハイブリッド/PHEV",
            "seating_capacity": 5,
        },
        "target_needs": ["fuel_efficiency", "technology", "design", "safety"],
    },
    {
        "model_name": "UX",
        "category": "SUV",
        "features": ["エントリーSUV", "都市走行最適化", "コンパクトボディ", "EV設定あり"],
        "safety_features": ["レクサスセーフティシステム+", "インテリジェントクリアランスソナー"],
        "technology": ["10.3インチナビ", "スマートフォン連携", "先進安全装備"],
        "specs": {
            "price_range": "4,200,000〜5,500,000円",
            "fuel_type": "ハイブリッド/EV",
            "seating_capacity": 5,
        },
        "target_needs": ["fuel_efficiency", "design", "technology"],
    },
    {
        "model_name": "TX",
        "category": "SUV",
        "features": ["3列シート大型SUV", "ファミリー向け", "広い室内空間", "上質な内装"],
        "safety_features": ["レクサスセーフティシステム+", "後席モニタリングシステム"],
        "technology": ["14インチタッチスクリーン", "後席エンターテインメント", "ヘッドアップディスプレイ"],
        "specs": {
            "price_range": "8,500,000〜11,000,000円",
            "fuel_type": "ハイブリッド",
            "seating_capacity": 7,
        },
        "target_needs": ["space", "family", "safety", "comfort"],
    },
    {
        "model_name": "RZ",
        "category": "SUV",
        "features": ["完全電気自動車", "SUVスタイル", "ステアバイワイヤ", "ゼロエミッション"],
        "safety_features": ["レクサスセーフティシステム+", "緊急操舵回避支援"],
        "technology": ["DIRECT4 AWD制御", "14インチタッチスクリーン", "ステアバイワイヤ技術"],
        "specs": {
            "price_range": "6,600,000〜8,000,000円",
            "fuel_type": "EV",
            "seating_capacity": 5,
        },
        "target_needs": ["technology", "fuel_efficiency", "design"],
    },
    {
        "model_name": "LS",
        "category": "SEDAN",
        "features": ["フラッグシップセダン", "最高級内装", "長距離快適性", "職人技のおもてなし"],
        "safety_features": ["レクサスセーフティシステム+A", "プロアクティブドライビングアシスト"],
        "technology": ["12.3インチデュアルスクリーン", "Mark Levinson 23スピーカー", "リラクゼーションシート"],
        "specs": {
            "price_range": "11,000,000〜18,000,000円",
            "fuel_type": "ハイブリッド",
            "seating_capacity": 5,
        },
        "target_needs": ["comfort", "technology", "safety", "design"],
    },
    {
        "model_name": "ES",
        "category": "SEDAN",
        "features": ["ミッドサイズセダン", "上質な乗り心地", "静粛性", "エレガントデザイン"],
        "safety_features": ["レクサスセーフティシステム+A", "後方クロストラフィックアラート"],
        "technology": ["12.3インチナビ", "デジタルアウターミラー", "ワイヤレス充電"],
        "specs": {
            "price_range": "5,500,000〜8,000,000円",
            "fuel_type": "ハイブリッド",
            "seating_capacity": 5,
        },
        "target_needs": ["comfort", "safety", "fuel_efficiency"],
    },
    {
        "model_name": "IS",
        "category": "SEDAN",
        "features": ["スポーツセダン", "走りの楽しさ", "コンパクトボディ", "ドライバーズカー"],
        "safety_features": ["レクサスセーフティシステム+A", "プリクラッシュセーフティ"],
        "technology": ["10.3インチナビ", "AVS（アダプティブ可変サスペンション）", "スポーツサウンドジェネレーター"],
        "specs": {
            "price_range": "4,400,000〜6,200,000円",
            "fuel_type": "ハイブリッド/ガソリン",
            "seating_capacity": 5,
        },
        "target_needs": ["design", "comfort", "technology"],
    },
    {
        "model_name": "RC",
        "category": "SEDAN",
        "features": ["2ドアクーペ", "スポーティスタイル", "個性的デザイン", "走行性能"],
        "safety_features": ["レクサスセーフティシステム+", "プリクラッシュセーフティ"],
        "technology": ["10.3インチナビ", "スポーツ走行モード", "パドルシフト"],
        "specs": {
            "price_range": "5,200,000〜7,200,000円",
            "fuel_type": "ハイブリッド/ガソリン",
            "seating_capacity": 4,
        },
        "target_needs": ["design", "comfort"],
    },
    {
        "model_name": "LC",
        "category": "SEDAN",
        "features": ["ラグジュアリークーペ", "芸術的デザイン", "高性能エンジン", "最上級スポーツ"],
        "safety_features": ["レクサスセーフティシステム+A", "車線逸脱防止支援システム"],
        "technology": ["10.3インチマルチメディア", "Mark Levinson プレミアムサウンド", "可変ギア比ステアリング"],
        "specs": {
            "price_range": "11,000,000〜14,000,000円",
            "fuel_type": "ハイブリッド/ガソリン",
            "seating_capacity": 4,
        },
        "target_needs": ["design", "comfort", "technology"],
    },
    {
        "model_name": "LM",
        "category": "MINIVAN",
        "features": ["ラグジュアリーミニバン", "VIP仕様", "4〜7人乗り", "最上級移動空間"],
        "safety_features": ["レクサスセーフティシステム+A", "後席乗降安全確認機能"],
        "technology": ["26インチ後席モニター", "4ゾーン独立温度調整", "防音ガラス"],
        "specs": {
            "price_range": "10,000,000〜20,000,000円",
            "fuel_type": "ハイブリッド",
            "seating_capacity": 4,
        },
        "target_needs": ["comfort", "space", "family", "technology"],
    },
    {
        "model_name": "LBX",
        "category": "SUV",
        "features": ["コンパクトラグジュアリークロスオーバー", "個性的デザイン", "都市型プレミアム", "コンパクトボディ"],
        "safety_features": ["レクサスセーフティシステム+A", "プリクラッシュセーフティ", "レーンキープアシスト"],
        "technology": ["9.8インチマルチメディア", "ワイヤレス充電", "先進ハイブリッドシステム"],
        "specs": {
            "price_range": "4,990,000〜7,500,000円",
            "fuel_type": "ハイブリッド",
            "seating_capacity": 5,
        },
        "target_needs": ["design", "fuel_efficiency", "technology", "comfort"],
    },
]


# ── PDF extraction via Claude API ─────────────────────────────────────────────

# 送信するPDFの優先順位（上位MAX_PDF_COUNTファイルのみ使用）
PDF_PRIORITY = [
    "specificationslist",   # スペック表（最重要）
    "pricelist",            # 価格表
    "equipmentlist",        # 装備表
]
MAX_PDF_COUNT = 3           # 1リクエストあたり最大3ファイル
MAX_SINGLE_PDF_SIZE = 5 * 1024 * 1024   # 1ファイル上限 5MB
MAX_TOTAL_PDF_SIZE = 8 * 1024 * 1024    # 合計上限 8MB

EXTRACT_PROMPT = """これらのPDFはLexus（レクサス）の自動車カタログ資料です（スペック表・価格表・装備表・スタイル集）。
これらを総合して、この車種の情報を以下のJSON形式で1件にまとめてください。

出力形式（JSONのみ・コードブロック不要・配列で1要素）:
[
  {{
    "model_name": "{model_name}",
    "category": "<SUV|SEDAN|MINIVAN>",
    "features": ["<車種の主要特徴1>", "<特徴2>", "<特徴3>", "<特徴4>"],
    "safety_features": ["<安全機能1>", "<安全機能2>", "<安全機能3>"],
    "technology": ["<先進技術・装備1>", "<技術2>", "<技術3>"],
    "grades": ["<グレード名1>", "<グレード名2>"],
    "specs": {{
      "price_range": "<最低価格〜最高価格（円、例: 9,570,000〜14,080,000円）>",
      "fuel_type": "<燃料タイプ（ガソリン/ハイブリッド/PHEV/EV）>",
      "seating_capacity": <定員数（整数）>,
      "engine": "<エンジン型式または排気量>",
      "dimensions": "<全長×全幅×全高 mm>"
    }},
    "target_needs": ["<ニーズ1>", "<ニーズ2>", "<ニーズ3>"]
  }}
]

target_needs は以下から該当するものを選択（3〜5個）:
safety, space, fuel_efficiency, comfort, design, technology, family, offroad"""


def _select_pdfs_for_model(model_dir: Path) -> list[Path]:
    """
    モデルフォルダから送信するPDFを選択する。
    優先順位の高いファイルから順に、サイズ上限内で最大MAX_PDF_COUNT件。
    """
    all_pdfs = {p.stem.lower(): p for p in model_dir.glob("*.pdf")}
    selected = []
    total_size = 0

    # 優先ファイルを順番に追加
    for priority_name in PDF_PRIORITY:
        if len(selected) >= MAX_PDF_COUNT:
            break
        # stem に priority_name を含むファイルを探す
        match = next(
            (p for stem, p in all_pdfs.items() if priority_name in stem),
            None,
        )
        if match is None:
            continue
        size = match.stat().st_size
        if size > MAX_SINGLE_PDF_SIZE:
            print(f"    Skip {match.name} ({size//1024}KB > {MAX_SINGLE_PDF_SIZE//1024}KB limit)")
            continue
        if total_size + size > MAX_TOTAL_PDF_SIZE:
            print(f"    Skip {match.name} (would exceed total {MAX_TOTAL_PDF_SIZE//1024//1024}MB limit)")
            break
        selected.append(match)
        total_size += size

    return selected


def extract_from_model_dir(
    model_name: str, model_dir: Path, client: anthropic.Anthropic
) -> dict | None:
    """モデルフォルダ内のPDFをまとめてClaudeに送り、1車種分のデータを抽出する。"""
    pdf_files = _select_pdfs_for_model(model_dir)
    if not pdf_files:
        print(f"  [WARN] No usable PDFs in {model_dir}")
        return None

    pdf_summary = ", ".join(f"{p.name}({p.stat().st_size//1024}KB)" for p in pdf_files)
    print(f"  {model_name}: {len(pdf_files)} PDFs -- {pdf_summary}")

    # メッセージコンテンツを構築（複数PDF + テキスト）
    content = []
    loaded = []
    for pdf_path in pdf_files:
        try:
            pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")
            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
                "title": pdf_path.name,
            })
            loaded.append(pdf_path.name)
        except Exception as e:
            print(f"  [WARN] Could not read {pdf_path.name}: {e}")

    if not loaded:
        return None

    content.append({
        "type": "text",
        "text": EXTRACT_PROMPT.format(model_name=model_name),
    })

    # Haiku はレート制限が高い（Opus: 30k tokens/min → Haiku: 100k+）
    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": content}],
            )
            break
        except anthropic.BadRequestError as e:
            print(f"  [WARN] Request too large for {model_name}: {e}")
            # PDFを1つ減らして再試行
            if len(content) > 2:
                content.pop(-2)  # 最後のdocumentを除去
                print(f"  Retrying with {len(content)-1} PDF(s)...")
                continue
            return None
        except anthropic.RateLimitError as e:
            wait = 30 * (attempt + 1)
            print(f"  [WARN] Rate limit hit, waiting {wait}s... (attempt {attempt+1}/3)")
            time.sleep(wait)
        except Exception as e:
            print(f"  [ERROR] API error for {model_name}: {e}")
            return None
    else:
        print(f"  [ERROR] All retries failed for {model_name}")
        return None

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```\w*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        data = json.loads(raw)
        if isinstance(data, list) and data:
            result = data[0]
        elif isinstance(data, dict):
            result = data
        else:
            raise ValueError(f"Unexpected structure: {type(data)}")
        result["model_name"] = model_name
        price = result.get('specs', {}).get('price_range', '?')
        print(f"  [OK] {model_name} -- {result.get('category')} -- price: {price}")
        return result
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse failed for {model_name}: {e}")
        print(f"  Raw: {raw[:400]}")
        return None


def _find_model_dirs() -> dict[str, Path]:
    """
    PDFディレクトリ構造を解析してモデル名 → フォルダのマッピングを返す。
    サブフォルダ方式（RZ/, LX/, GX/）とフラット方式の両方に対応。
    """
    models: dict[str, Path] = {}
    if not PDF_DIR.exists():
        return models

    # サブフォルダ方式: PDF_DIR/<MODEL_NAME>/*.pdf
    for subdir in sorted(PDF_DIR.iterdir()):
        if subdir.is_dir() and list(subdir.glob("*.pdf")):
            model_name = subdir.name.upper()
            models[model_name] = subdir

    return models


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    model_dirs = _find_model_dirs()
    flat_pdfs = sorted(PDF_DIR.glob("*.pdf")) if PDF_DIR.exists() else []

    has_pdf_data = bool(model_dirs or flat_pdfs)

    if has_pdf_data:
        if not ANTHROPIC_API_KEY:
            print("[ERROR] ANTHROPIC_API_KEY not set — cannot process PDFs")
            print("  Set: $env:ANTHROPIC_API_KEY = 'sk-ant-...'")
            raise SystemExit(1)

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        products_raw: list[dict] = []

        if model_dirs:
            print(f"Found {len(model_dirs)} model folder(s): {', '.join(model_dirs.keys())}")
            for model_name, model_dir in model_dirs.items():
                result = extract_from_model_dir(model_name, model_dir, client)
                if result:
                    products_raw.append(result)
                else:
                    print(f"  [WARN] Falling back to built-in data for {model_name}")
                time.sleep(5)  # API rate limit buffer

        elif flat_pdfs:
            # フラット方式（後方互換）: 1PDF = 1リクエスト
            print(f"Found {len(flat_pdfs)} PDF(s) in flat layout")
            for pdf_path in flat_pdfs:
                model_name = pdf_path.stem.upper()
                # 単一PDFで一時フォルダとして扱う（簡易対応）
                result = extract_from_model_dir(
                    model_name, pdf_path.parent, client
                )
                if result:
                    products_raw.append(result)
                time.sleep(2)

        # フォールバックで残りの10モデル（RZ/LX/GX以外）を補完
        extracted_models = {p["model_name"].upper() for p in products_raw}
        supplemented = 0
        for fb in FALLBACK_PRODUCTS:
            if fb["model_name"].upper() not in extracted_models:
                products_raw.append(fb)
                extracted_models.add(fb["model_name"].upper())
                supplemented += 1

        if supplemented:
            print(f"Supplemented {supplemented} model(s) from fallback data")

        products = products_raw

    else:
        print(f"No PDFs found in {PDF_DIR}")
        print("Using built-in fallback data for all 13 Lexus models")
        products = FALLBACK_PRODUCTS

    # 重複除去（同一model_nameは先勝ち = PDF抽出データ優先）
    seen: dict[str, dict] = {}
    for p in products:
        key = p.get("model_name", "").upper()
        if key not in seen:
            seen[key] = p
    final_products = list(seen.values())

    OUTPUT_PATH.write_text(
        json.dumps(final_products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved {len(final_products)} models → {OUTPUT_PATH}")
    for p in final_products:
        src = "PDF" if p.get("grades") else "fallback"
        print(f"  {p['model_name']:6s} [{p.get('category','?')}] ({src})  "
              f"needs: {p.get('target_needs', [])}")


if __name__ == "__main__":
    main()
