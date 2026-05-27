"""
Phase 6 & 9: FastAPI recommendation + product import endpoints
"""
import json
import os
import re
import subprocess
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic

from api.demo.router import router as demo_router
from engine.recommendation_engine import RecommendationEngine, RecommendationRequest
from graph.graph_builder import (
    GraphBuilder,
    _categorize_purchase_driver,
    _kikkake_to_trigger,
    _kikkake_to_life_event,
    TRIGGER_LABELS,
    LIFE_EVENT_LABELS,
    DECISION_STYLE_MASTER,
    REGRET_CATEGORY_LABELS,
    _PURCHASE_DRIVER_CATEGORIES,
)
# 後方互換エイリアス（v3移行で削除されたシンボルを補完）
_SUB_TRIGGER_CATEGORIES     = TRIGGER_LABELS
_categorize_sub_trigger     = _kikkake_to_trigger
DECISION_STYLE_LABELS       = {k: v["label"]       for k, v in DECISION_STYLE_MASTER.items()}
DECISION_STYLE_DESCRIPTIONS = {k: v["description"] for k, v in DECISION_STYLE_MASTER.items()}
from crawler.web_scraper import (
    discover_vehicles_from_maker,
    scan_vehicle_url,
    scan_url_list,
    scan_maker_url,
)

app = FastAPI(title="Decision Intelligence PoC", version="1.0.0")

_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8501",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(demo_router)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PRODUCTS_PATH = Path("data/raw/products.json")
CONSUMER_STORIES_PATH = Path("data/raw/consumer_stories.json")
CONSUMER_DECISIONS_PATH = Path("data/processed/consumer_decisions.json")
VERIFICATION_LOG_PATH = Path("data/processed/verification_log.json")
PDF_CATALOG_DIR = Path("data/raw/lexus_catalogs")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


# ── Request / Response models ──────────────────────────────────────────────

class RecommendRequest(BaseModel):
    family_size: int = 4
    needs: list[str] = ["safety", "space"]
    budget: int = 5_000_000
    usage: Optional[str] = ""
    free_text: Optional[str] = ""


class AppealPoint(BaseModel):
    text: str                        # カタログ原文
    score: int = 0                   # ニーズマッチスコア（2点/ニーズ）
    matched_needs: list[str] = []    # マッチしたニーズ名
    matched_keywords: list[str] = [] # 実際にヒットしたキーワード


class RecommendationItem(BaseModel):
    model: str
    score: float
    reason: str
    similar_consumers: list[str] = []
    grades: list[str] = []           # カタログから取得したグレード一覧
    quick_grade: str = ""            # ルールベースで選んだ推薦グレード
    price_range: str = ""
    fuel_type: str = ""
    seating_capacity: int = 0
    appeal_points: list[AppealPoint] = []  # ニーズマッチ上位10件（LLM不使用）


class RecommendResponse(BaseModel):
    recommendations: list[RecommendationItem]


class ExplainRequest(BaseModel):
    model_name: str
    family_size: int = 4
    needs: list[str] = []
    budget: int = 0
    usage: str = ""
    free_text: str = ""
    selected_points: list[str] = []  # UIで選択された訴求ポイント


class ExplainResponse(BaseModel):
    model_name: str
    recommended_grade: str
    appeal_points: list[AppealPoint] = []  # 選択ポイント（エコーバック）
    talk_examples: list[str] = []          # LLM生成の営業トーク3例


class StoryText(BaseModel):
    purchase_trigger: str = ""
    purchase_story: str = ""
    deciding_factor: str = ""
    advice: str = ""


class SalesFeedback(BaseModel):
    consumer_id: str                        # UI で自動生成
    title: str = ""
    gender: str = ""
    age_group: str = ""
    location: str = ""
    vehicle_model: str
    grade: str = ""
    kikkake: str = ""
    most_satisfied: str = ""
    satisfaction_score: int = 5             # 1〜5
    story_text: Optional[StoryText] = None
    considered_options: list[str] = []
    comment: str = ""                       # 旧フィールド互換
    # New Consumer enrichment fields
    occupation: str = ""
    income_range: str = ""
    driving_frequency: str = ""   # "毎日" / "週数回" / "週末のみ" / "月数回"
    mobility_pattern: str = ""    # "通勤" / "レジャー" / "長距離" / "市街地" / "複合"
    values: str = ""              # 自由記述: "安全重視" など
    physical_notes: str = ""      # 自由記述: 任意
    # New PurchaseDriver
    purchase_driver: str = ""     # 決め手テキスト（自由記述）
    # 国（デフォルト：日本）
    country: str = "日本"


# ── Verification models ────────────────────────────────────────────────────

class VerificationField(BaseModel):
    """1フィールド分の検証結果。"""
    extracted: Any = None          # グラフビルダーが抽出した値
    is_correct: bool = True        # 正しいか
    corrected: Any = None          # 誤りの場合の正解値
    source_text: str = ""          # 抽出元テキスト（改善分析に使用）
    note: str = ""                 # 自由メモ


class VerificationRecord(BaseModel):
    story_id: str
    verified_at: str
    fields: dict[str, VerificationField]


class GraphExplorerRequest(BaseModel):
    # Consumer 属性フィルター（複数選択 = OR）
    gender:             list[str] = []
    age_group:          list[str] = []
    location:           list[str] = []
    country:            list[str] = []
    occupation:         list[str] = []
    income_range:       list[str] = []
    driving_frequency:  list[str] = []
    mobility_pattern:   list[str] = []
    # 拡張オントロジーノードフィルター
    decision_style:     list[str] = []
    life_event:         list[str] = []
    regret:             list[str] = []
    # グラフノードフィルター（選択値に接続する Consumer に絞り込む）
    trigger:            list[str] = []
    need:               list[str] = []
    sub_need:           list[str] = []
    evaluation_criteria:list[str] = []
    purchase_driver:    list[str] = []
    vehicle_model:      list[str] = []
    feature:            list[str] = []


class SimilarStoriesRequest(BaseModel):
    needs: list[str]
    family_size: int = 4
    limit: int = 5


class ImportProductRequest(BaseModel):
    product_page_url: str


class ImportProductResponse(BaseModel):
    status: str
    model_name: str
    message: str


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_engine() -> RecommendationEngine:
    return RecommendationEngine()


def _get_builder() -> GraphBuilder:
    return GraphBuilder()


def _load_products() -> list[dict]:
    if PRODUCTS_PATH.exists():
        return json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    return []


def _get_product(model_name: str) -> dict:
    return next(
        (p for p in _load_products() if p["model_name"].upper() == model_name.upper()),
        {},
    )


# ニーズ × フィーチャー キーワードマッピング（カタログ語彙に合わせる）
_NEED_KEYWORDS: dict[str, list[str]] = {
    "safety":         ["安全", "セーフティ", "Safety", "衝突", "プリクラッシュ",
                       "レーン", "アシスト", "ブレーキ", "モニター", "警告", "予防"],
    "space":          ["空間", "広", "ラゲッジ", "室内", "3列", "7人", "収納",
                       "トランク", "荷室", "キャビン", "ルーフ"],
    "fuel_efficiency":["燃費", "ハイブリッド", "電気", "EV", "PHEV", "充電",
                       "エコ", "低燃費", "回生", "プラグイン"],
    "comfort":        ["快適", "乗り心地", "静粛", "シート", "クルーズ", "サスペンション",
                       "防音", "温度", "クライメート", "マッサージ", "リクライニング"],
    "design":         ["デザイン", "スタイル", "スポーティ", "外観", "インテリア",
                       "LED", "ホイール", "カラー", "シルエット", "フォルム"],
    "technology":     ["ナビ", "ディスプレイ", "デジタル", "コネクト", "OTA",
                       "自動", "AI", "テクノロジー", "HUD", "カメラ"],
    "family":         ["ファミリー", "子ども", "チャイルド", "スライド", "3列",
                       "7人", "後席", "キャプテン", "助手席"],
    "offroad":        ["オフロード", "四駆", "AWD", "4WD", "悪路", "クロスカントリー",
                       "KDSS", "ヒルスタート", "ダウンヒル"],
}


def _pick_grade(grades: list[str], family_size: int, needs: list[str]) -> str:
    """ルールベースでグレードを1つ選ぶ（LLM不使用）。"""
    if not grades:
        return "標準グレード"

    # 定員マッチング
    if family_size >= 7:
        for g in grades:
            if "7" in g:
                return g
    if family_size >= 5:
        for g in grades:
            if "5" in g or "7" in g:
                return g

    # ニーズマッチング
    if "offroad" in needs:
        for g in grades:
            if any(kw.upper() in g.upper() for kw in ["OVERTRAIL", "OFF", "4WD", "AWD"]):
                return g
    if "design" in needs or "technology" in needs:
        for g in grades:
            if any(kw.upper() in g.upper() for kw in ["F SPORT", "FSPORT", "SPORT"]):
                return g

    return grades[0]


def _score_features(features: list[str], needs: list[str]) -> list[AppealPoint]:
    """ニーズとの合致度でフィーチャーをスコアリングし、上位10件をマッチ根拠付きで返す。"""
    scored: list[AppealPoint] = []
    for feat in features:
        matched_needs: list[str] = []
        matched_kws: list[str] = []
        for need in needs:
            keywords = _NEED_KEYWORDS.get(need, [])
            hit = [kw for kw in keywords if kw in feat]
            if hit:
                matched_needs.append(need)
                matched_kws.extend(hit)
        # 重複キーワードを除去しつつ順序を保持
        seen: set[str] = set()
        deduped_kws = [k for k in matched_kws if not (k in seen or seen.add(k))]  # type: ignore[func-returns-value]
        scored.append(AppealPoint(
            text=feat,
            score=len(matched_needs) * 2,
            matched_needs=matched_needs,
            matched_keywords=deduped_kws,
        ))

    scored.sort(key=lambda x: -x.score)
    result = [p for p in scored if p.score > 0]
    if len(result) < 10:
        result += [p for p in scored if p.score == 0]
    return result[:10]


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Neo4j 確認はデモ起動を遅らせないようスキップ可能（環境変数 HEALTH_SKIP_NEO4J）。"""
    if os.environ.get("HEALTH_SKIP_NEO4J", "").lower() in ("1", "true", "yes"):
        return {"status": "ok", "neo4j": "skipped"}
    neo4j_status = "unavailable"
    try:
        engine = _get_engine()
        # verify_connectivity は環境によって 10 秒以上かかることがある
        with engine.driver.session() as session:
            session.run("RETURN 1").consume()
        neo4j_status = "connected"
        engine.close()
    except Exception:
        pass
    return {"status": "ok", "neo4j": neo4j_status}


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    engine = _get_engine()
    try:
        reco_req = RecommendationRequest(
            family_size=req.family_size,
            budget=req.budget,
            needs=req.needs,
            usage=req.usage or "",
        )
        results = engine.recommend(reco_req, top_k=5)
        if not results:
            raise HTTPException(status_code=404, detail="No recommendations found")

        items = []
        for r in results:
            product = _get_product(r.model)
            grades = product.get("grades", [])
            specs = product.get("specs", {})
            features = (
                product.get("features", [])
                + product.get("safety_features", [])
                + product.get("technology", [])
            )
            items.append(RecommendationItem(
                model=r.model,
                score=r.score,
                reason=r.reason,
                similar_consumers=r.similar_consumers,
                grades=grades,
                quick_grade=_pick_grade(grades, req.family_size, req.needs),
                price_range=specs.get("price_range", ""),
                fuel_type=specs.get("fuel_type", ""),
                seating_capacity=specs.get("seating_capacity", 0) or 0,
                appeal_points=_score_features(features, req.needs),
            ))
        return RecommendResponse(recommendations=items)
    finally:
        engine.close()


@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    """推薦グレード（ルールベース）、訴求ポイント（カタログ実データ）、営業トーク3例（Claude）を返す。"""
    product = _get_product(req.model_name)
    grades = product.get("grades", [])
    features = (
        product.get("features", [])
        + product.get("safety_features", [])
        + product.get("technology", [])
    )
    specs = product.get("specs", {})
    price_range = specs.get("price_range", "")
    seating = specs.get("seating_capacity", 5)

    # グレード選択（ルールベース、LLM不使用）
    recommended_grade = _pick_grade(grades, req.family_size, req.needs)

    # 訴求ポイント：UI選択済みを優先（AppealPoint に変換）、なければスコアリング
    if req.selected_points:
        appeal_points = [AppealPoint(text=p) for p in req.selected_points]
    else:
        appeal_points = _score_features(features, req.needs) or [AppealPoint(text=f) for f in features[:10]]

    # 営業トーク3例（Claude Haiku 生成）
    talk_examples: list[str] = []
    if ANTHROPIC_API_KEY:
        budget_man = req.budget // 10_000 if req.budget else 0
        points_text = "\n".join(f"・{p.text}" for p in appeal_points)
        prompt = f"""あなたはレクサスの優秀な営業コンサルタントです。
以下の顧客情報と訴求ポイントを踏まえ、お客様に響く営業トーク例を3つ書いてください。
それぞれ異なるアプローチで、自然な日本語の会話調にしてください。

【顧客情報】
・家族人数: {req.family_size}人
・予算: {budget_man}万円
・重視するポイント: {', '.join(req.needs)}
・用途: {req.usage or '未指定'}
{f'・担当者メモ: {req.free_text}' if req.free_text else ''}

【推薦車種: Lexus {req.model_name} — {recommended_grade}】
・価格帯: {price_range}
・定員: {seating}人

【訴求ポイント（カタログ実データ）】
{points_text}

以下のJSON形式のみで回答してください（コードブロック不要）:
{{
  "talk_examples": [
    "<営業トーク1: 2〜3文。お客様の課題や生活シーンに寄り添い、訴求ポイントを自然に組み込む>",
    "<営業トーク2: 別の角度（安心感・価値・体験）から訴求>",
    "<営業トーク3: クロージング寄り。背中を押す一言＋次のアクション提案>"
  ]
}}"""
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            talk_examples = data.get("talk_examples", [])
        except Exception:
            pass

    if not talk_examples:
        needs_ja = "・".join(req.needs[:2]) if req.needs else "お客様のニーズ"
        talk_examples = [
            f"Lexus {req.model_name} は{needs_ja}を重視されるお客様に最適な一台です。"
            f"ぜひ実車でその違いをお確かめください。",
        ]

    return ExplainResponse(
        model_name=req.model_name,
        recommended_grade=recommended_grade,
        appeal_points=appeal_points,
        talk_examples=talk_examples,
    )


@app.post("/similar_stories")
def similar_stories(req: SimilarStoriesRequest):
    """同じニーズを持つ既存顧客の購買ストーリーを返す（Tab2用）。"""
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Consumer)-[:HAS_NEED]->(n:Need)
                WHERE n.name IN $needs
                WITH c, count(DISTINCT n) AS matched
                WHERE matched >= $min_match
                MATCH (c)-[:SELECTED]->(v:VehicleModel)
                RETURN c.id AS consumer_id,
                       c.title AS title,
                       c.family_size AS family_size,
                       c.usage AS usage,
                       v.name AS selected_vehicle,
                       matched
                ORDER BY matched DESC,
                         abs(COALESCE(c.family_size, 3) - $family_size) ASC
                LIMIT $limit
                """,
                needs=req.needs,
                min_match=max(1, len(req.needs) // 2),
                family_size=req.family_size,
                limit=req.limit,
            )
            consumers = [dict(r) for r in result]
    finally:
        builder.close()

    # consumer_stories.json から詳細を補完
    stories_map: dict[str, dict] = {}
    if CONSUMER_STORIES_PATH.exists():
        for s in json.loads(CONSUMER_STORIES_PATH.read_text(encoding="utf-8")):
            stories_map[s["story_id"]] = s

    enriched = []
    for c in consumers:
        story = stories_map.get(c["consumer_id"], {})
        st = story.get("story_text", {})
        enriched.append({
            **c,
            "gender": story.get("gender", ""),
            "age_group": story.get("age_group", ""),
            "kikkake": story.get("kikkake", ""),
            "most_satisfied": story.get("most_satisfied", ""),
            "satisfaction_score": story.get("satisfaction_score", ""),
            "purchase_trigger": st.get("purchase_trigger", "") if isinstance(st, dict) else "",
            "deciding_factor": st.get("deciding_factor", "") if isinstance(st, dict) else "",
        })

    return {"consumers": enriched}


@app.post("/sales_feedback")
def sales_feedback(feedback: SalesFeedback):
    """販売結果を記録: グラフ重み更新 + consumer_stories.json に追記。"""
    satisfaction = (feedback.satisfaction_score - 1) / 4.0  # 1→0.0, 5→1.0
    weight_delta = (satisfaction - 0.5) * 0.2

    # グラフ重み更新
    builder = _get_builder()
    try:
        builder.update_selection_weight(
            consumer_id=feedback.consumer_id,
            vehicle_name=feedback.vehicle_model,
            weight_delta=weight_delta,
        )
    finally:
        builder.close()

    # PurchaseDriver graph node
    if feedback.purchase_driver or (feedback.story_text and feedback.story_text.deciding_factor):
        deciding_text = feedback.purchase_driver or feedback.story_text.deciding_factor
        from graph.graph_builder import _categorize_purchase_driver
        pd_category = _categorize_purchase_driver(deciding_text)
        builder2 = _get_builder()
        try:
            with builder2.driver.session() as session:
                session.run("""
                    MERGE (pd:PurchaseDriver {name: $category})
                    ON CREATE SET pd.raw_text = $raw_text
                    WITH pd
                    MATCH (c:Consumer {id: $cid})
                    MERGE (c)-[:DECIDED]->(pd)
                """, category=pd_category, raw_text=deciding_text[:200], cid=feedback.consumer_id)
        finally:
            builder2.close()

    # consumer_stories.json に追記
    today = date.today()
    post_date = f"{today.year}年{today.month}月{today.day}日"
    story: dict = {
        "story_id": feedback.consumer_id,
        "title": feedback.title or f"{feedback.vehicle_model}購入",
        "gender": feedback.gender,
        "age_group": feedback.age_group,
        "location": feedback.location,
        "grade": feedback.grade,
        "post_date": post_date,
        "vehicle_model": feedback.vehicle_model,
        "kikkake": feedback.kikkake,
        "most_satisfied": feedback.most_satisfied,
        "satisfaction_score": feedback.satisfaction_score,
        "story_text": feedback.story_text.model_dump() if feedback.story_text else {},
        "considered_options": feedback.considered_options,
        "occupation": feedback.occupation,
        "income_range": feedback.income_range,
        "driving_frequency": feedback.driving_frequency,
        "mobility_pattern": feedback.mobility_pattern,
        "values": feedback.values,
        "physical_notes": feedback.physical_notes,
        "purchase_driver": feedback.purchase_driver,
        "country": feedback.country,
    }
    try:
        if CONSUMER_STORIES_PATH.exists():
            stories = json.loads(CONSUMER_STORIES_PATH.read_text(encoding="utf-8"))
        else:
            stories = []
        stories.append(story)
        CONSUMER_STORIES_PATH.write_text(
            json.dumps(stories, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "consumer_id": feedback.consumer_id,
        "weight_delta": weight_delta,
        "message": f"{feedback.vehicle_model} の販売記録を保存しました",
    }


@app.post("/rescan_catalog")
def rescan_catalog():
    """data/raw/lexus_catalogs/ の PDF を再スキャンしてグラフを更新する。"""
    results: dict[str, str] = {}
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    # Step 1: product_scraper
    r1 = subprocess.run(
        ["python", "-m", "crawler.product_scraper"],
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=300, env=env,
    )
    results["scraper"] = "ok" if r1.returncode == 0 else f"error: {r1.stderr[-300:]}"

    # Step 2: product_extractor
    r2 = subprocess.run(
        ["python", "-m", "extractor.product_extractor"],
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=120, env=env,
    )
    results["extractor"] = "ok" if r2.returncode == 0 else f"error: {r2.stderr[-300:]}"

    # Step 3: グラフの製品ノードだけ更新（コンシューマーデータは保持）
    if r2.returncode == 0:
        builder = _get_builder()
        try:
            builder.load_product_features()
            results["graph"] = "ok"
        except Exception as e:
            results["graph"] = f"error: {e}"
        finally:
            builder.close()

    new_count = len(_load_products())
    all_ok = all(v == "ok" for v in results.values())
    return {
        "status": "ok" if all_ok else "partial",
        "steps": results,
        "model_count": new_count,
        "message": f"カタログをスキャンし {new_count} 車種を更新しました",
    }


# ── Webスキャン エンドポイント ────────────────────────────────────────────────

def _graph_load_product_features() -> str:
    """
    product_features.json の内容を Neo4j グラフに反映する。
    rescan_catalog の Step 3 と同等の処理。成功時 "ok"、失敗時エラーメッセージを返す。
    """
    builder = _get_builder()
    try:
        builder.load_product_features()
        return "ok"
    except Exception as e:
        return f"error: {e}"
    finally:
        builder.close()


class WebScanVehicleRequest(BaseModel):
    model_name: str       # 例: "INSIGHT"
    url: str              # 例: "https://www.honda.co.jp/INSIGHT/"
    update_graph: bool = True


class WebScanMakerRequest(BaseModel):
    url: str              # 例: "https://www.honda.co.jp/auto/"
    max_vehicles: int = 10
    update_graph: bool = True


class WebDiscoverRequest(BaseModel):
    url: str              # メーカーTOP URL


class WebScanUrlListItem(BaseModel):
    model_name: str
    url: str


class WebScanUrlListRequest(BaseModel):
    vehicles: list[WebScanUrlListItem]
    update_graph: bool = True


@app.post("/rescan_web/vehicle")
def rescan_web_vehicle(req: WebScanVehicleRequest):
    """
    車種TOP URLをスキャンしてグラフを更新する。
    配下のサブページ（webcatalog/type/list/ など）も自動的に収集する。
    Step 1: webスキャン → products.json
    Step 2: product_extractor → product_features.json
    Step 3: load_product_features → Neo4j  ← 追加
    """
    if not req.model_name.strip():
        raise HTTPException(status_code=400, detail="model_name は必須です")
    if not req.url.strip().startswith("http"):
        raise HTTPException(status_code=400, detail="有効なURLを入力してください")

    result = scan_vehicle_url(
        model_name=req.model_name.strip().upper(),
        url=req.url.strip(),
        update_graph=req.update_graph,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "スキャン失敗"))

    # Step 3: product_features.json → Neo4j（rescan_catalog と同等）
    if req.update_graph:
        graph_status = _graph_load_product_features()
        result.setdefault("graph_steps", {})["graph"] = graph_status

    new_count = len(_load_products())
    return {**result, "total_model_count": new_count}


@app.post("/rescan_web/discover")
def rescan_web_discover(req: WebDiscoverRequest):
    """
    メーカーTOP URLをスキャンし、検出された車種URL一覧を返す（Claude呼び出しなし）。
    実際のスキャン前の確認用。
    """
    if not req.url.strip().startswith("http"):
        raise HTTPException(status_code=400, detail="有効なURLを入力してください")

    vehicles = discover_vehicles_from_maker(req.url.strip())
    return {
        "status": "ok",
        "count": len(vehicles),
        "vehicles": vehicles,
    }


@app.post("/rescan_web/maker")
def rescan_web_maker(req: WebScanMakerRequest):
    """
    メーカーTOP URLから車種を自動検出してすべてスキャンし、グラフを更新する。
    """
    if not req.url.strip().startswith("http"):
        raise HTTPException(status_code=400, detail="有効なURLを入力してください")

    result = scan_maker_url(
        maker_url=req.url.strip(),
        max_vehicles=max(1, min(req.max_vehicles, 25)),
        update_graph=req.update_graph,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "スキャン失敗"))

    # Step 3: product_features.json → Neo4j
    if req.update_graph and result.get("succeeded"):
        graph_status = _graph_load_product_features()
        result.setdefault("graph_steps", {})["graph"] = graph_status

    new_count = len(_load_products())
    return {**result, "total_model_count": new_count}


@app.post("/rescan_web/url-list")
def rescan_web_url_list(req: WebScanUrlListRequest):
    """
    URLリストを一括スキャンしてグラフを更新する。
    JSレンダリングのサイトでメーカーTOP自動検出が使えない場合の代替手段。
    """
    if not req.vehicles:
        raise HTTPException(status_code=400, detail="vehicles リストが空です")

    result = scan_url_list(
        vehicles=[{"model_name": v.model_name, "url": v.url} for v in req.vehicles],
        update_graph=req.update_graph,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "スキャン失敗"))

    # Step 3: product_features.json → Neo4j
    if req.update_graph and result.get("succeeded"):
        graph_status = _graph_load_product_features()
        result.setdefault("graph_steps", {})["graph"] = graph_status

    new_count = len(_load_products())
    return {**result, "total_model_count": new_count}


@app.post("/rescan_web/apply-graph")
def rescan_web_apply_graph():
    """
    既存の product_features.json を Neo4j に反映する（再スキャン不要）。
    過去にスキャン済みだが Neo4j 未反映の場合に使用する。
    """
    graph_status = _graph_load_product_features()
    count = len(_load_products())
    return {
        "status": "ok" if graph_status == "ok" else "error",
        "graph": graph_status,
        "total_model_count": count,
    }


@app.get("/graph/filter-values")
def graph_filter_values():
    """KG Explorer 用フィルター選択肢を返す（Consumer 属性 + ノード名一覧）。"""
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            fv: dict[str, Any] = {"consumer": {}}

            # Consumer 属性（カテゴリカル）
            for prop in ["gender", "age_group", "location", "country", "occupation",
                         "income_range", "driving_frequency", "mobility_pattern"]:
                r = session.run(
                    f"MATCH (c:Consumer) WHERE c.{prop} IS NOT NULL AND c.{prop} <> '' "
                    f"RETURN DISTINCT c.{prop} AS v ORDER BY v"
                )
                fv["consumer"][prop] = [row["v"] for row in r]

            # グラフノード（拡張オントロジー対応）
            node_queries = {
                "decision_style": (
                    "MATCH (ds:DecisionStyle) "
                    "MATCH (c:Consumer)-[:HAS_DECISION_STYLE]->(ds) "
                    "RETURN ds.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC"
                ),
                "life_event": (
                    "MATCH (le:LifeEvent) "
                    "MATCH (c:Consumer)-[:EXPERIENCED]->(le) "
                    "RETURN le.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC"
                ),
                "trigger": (
                    "MATCH (t:Trigger) "
                    "MATCH (c:Consumer)-[:HAS_TRIGGER]->(t) "
                    "RETURN t.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC"
                ),
                "need": (
                    "MATCH (n:Need) WHERE n.level = 'parent' OR n.level IS NULL "
                    "MATCH (c:Consumer)-[:HAS_NEED]->(n) "
                    "RETURN n.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC"
                ),
                "sub_need": (
                    "MATCH (n:Need {level: 'child'}) "
                    "MATCH (c:Consumer)-[:HAS_NEED]->(n) "
                    "RETURN n.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC"
                ),
                "evaluation_criteria": (
                    "MATCH (ec:EvaluationCriteria) "
                    "MATCH (c:Consumer)-[:VALUED]->(ec) "
                    "RETURN ec.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC LIMIT 50"
                ),
                "purchase_driver": (
                    "MATCH (pd:PurchaseDriver) "
                    "MATCH (c:Consumer)-[:DECIDED]->(pd) "
                    "RETURN pd.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC"
                ),
                "regret": (
                    "MATCH (r:Regret) "
                    "MATCH (c:Consumer)-[:HAS_REGRET]->(r) "
                    "RETURN r.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC"
                ),
                "vehicle_model": (
                    "MATCH (v:VehicleModel) "
                    "MATCH (c:Consumer)-[:SELECTED]->(v) "
                    "RETURN v.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC LIMIT 60"
                ),
                "feature": (
                    "MATCH (f:Feature) "
                    "MATCH (c:Consumer)-[:SELECTED]->(:VehicleModel)-[:HAS_FEATURE]->(f) "
                    "RETURN f.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC LIMIT 60"
                ),
            }
            for key, query in node_queries.items():
                r = session.run(query)
                fv[key] = [row["name"] for row in r if row["name"]]

            # グレード一覧（products.json から車種別に返す）
            fv["grades_by_vehicle"] = {
                p["model_name"]: p.get("grades", [])
                for p in _load_products()
            }

            return fv
    finally:
        builder.close()


def _build_explorer_where(req: GraphExplorerRequest) -> tuple[str, dict]:
    """WHERE句とパラメータを生成するヘルパー（graph_explorer / filter-values/dynamic 共用）。"""
    params: dict[str, Any] = {}
    conditions: list[str] = []

    # Consumer 属性フィルター
    for prop, vals in [
        ("gender",            req.gender),
        ("age_group",         req.age_group),
        ("location",          req.location),
        ("country",           req.country),
        ("occupation",        req.occupation),
        ("income_range",      req.income_range),
        ("driving_frequency", req.driving_frequency),
        ("mobility_pattern",  req.mobility_pattern),
    ]:
        if vals:
            conditions.append(f"c.{prop} IN ${prop}")
            params[prop] = vals

    # 拡張オントロジーノードフィルター
    if req.decision_style:
        conditions.append(
            "EXISTS { MATCH (c)-[:HAS_DECISION_STYLE]->(ds:DecisionStyle) "
            "WHERE ds.name IN $f_ds }"
        )
        params["f_ds"] = req.decision_style
    if req.life_event:
        conditions.append(
            "EXISTS { MATCH (c)-[:EXPERIENCED]->(le:LifeEvent) "
            "WHERE le.name IN $f_le }"
        )
        params["f_le"] = req.life_event
    if req.regret:
        conditions.append(
            "EXISTS { MATCH (c)-[:HAS_REGRET]->(r:Regret) "
            "WHERE r.name IN $f_regret }"
        )
        params["f_regret"] = req.regret

    # ノードフィルター（EXISTS 副問い合わせ）
    if req.trigger:
        conditions.append(
            "EXISTS { MATCH (c)-[:HAS_TRIGGER]->(tt:Trigger) "
            "WHERE tt.name IN $f_trigger }"
        )
        params["f_trigger"] = req.trigger
    if req.need:
        conditions.append(
            "EXISTS { MATCH (c)-[:HAS_NEED]->(nn:Need) WHERE nn.name IN $f_need }"
        )
        params["f_need"] = req.need
    if req.sub_need:
        conditions.append(
            "EXISTS { MATCH (c)-[:HAS_NEED]->(sn:Need {level: 'child'}) "
            "WHERE sn.name IN $f_sub_need }"
        )
        params["f_sub_need"] = req.sub_need
    if req.evaluation_criteria:
        conditions.append(
            "EXISTS { MATCH (c)-[:VALUED]->(ec2:EvaluationCriteria) "
            "WHERE ec2.name IN $f_ec }"
        )
        params["f_ec"] = req.evaluation_criteria
    if req.purchase_driver:
        conditions.append(
            "EXISTS { MATCH (c)-[:DECIDED]->(pd2:PurchaseDriver) "
            "WHERE pd2.name IN $f_pd }"
        )
        params["f_pd"] = req.purchase_driver
    if req.vehicle_model:
        conditions.append(
            "EXISTS { MATCH (c)-[:SELECTED]->(vm2:VehicleModel) "
            "WHERE vm2.name IN $f_vm }"
        )
        params["f_vm"] = req.vehicle_model
    if req.feature:
        conditions.append(
            "EXISTS { MATCH (c)-[:SELECTED]->(:VehicleModel)-[:HAS_FEATURE]->(ff:Feature) "
            "WHERE ff.name IN $f_feature }"
        )
        params["f_feature"] = req.feature

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


@app.post("/graph/explorer")
def graph_explorer(req: GraphExplorerRequest):
    """条件に合致する Consumer に繋がるノードをスコア順に返す。"""
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            where, params = _build_explorer_where(req)

            # Consumer 件数
            cr = session.run(f"MATCH (c:Consumer) {where} RETURN count(c) AS n", **params)
            consumer_count = cr.single()["n"]
            if consumer_count == 0:
                return {"consumer_count": 0, "results": {}}

            # 各ノードタイプ別に集計（スコア = 一致 Consumer 数）
            _queries: dict[str, str] = {
                "DecisionStyle": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_DECISION_STYLE]->(ds:DecisionStyle)
                    RETURN ds.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 10
                """,
                "LifeEvent": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:EXPERIENCED]->(le:LifeEvent)
                    RETURN le.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 15
                """,
                "Trigger": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_TRIGGER]->(t:Trigger)
                    RETURN t.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 20
                """,
                "Need": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_NEED]->(n:Need)
                    WHERE n.level = 'parent' OR n.level IS NULL
                    RETURN n.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 20
                """,
                "Sub-Need": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_NEED]->(n:Need {{level: 'child'}})
                    RETURN n.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 20
                """,
                "EvaluationCriteria": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:VALUED]->(ec:EvaluationCriteria)
                    RETURN ec.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 20
                """,
                "PurchaseDriver": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:DECIDED]->(pd:PurchaseDriver)
                    RETURN pd.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 20
                """,
                "Regret": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_REGRET]->(r:Regret)
                    RETURN r.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 15
                """,
                "VehicleModel": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:SELECTED]->(v:VehicleModel)
                    RETURN v.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 30
                """,
                "Feature": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:SELECTED]->(v:VehicleModel)-[:HAS_FEATURE]->(f:Feature)
                    RETURN f.name AS name, count(DISTINCT c) AS score
                    ORDER BY score DESC LIMIT 20
                """,
            }

            results: dict[str, list] = {}
            for node_type, query in _queries.items():
                r = session.run(query, **params)
                rows = [{"name": row["name"], "score": row["score"]} for row in r if row["name"]]
                if rows:
                    results[node_type] = rows

            return {"consumer_count": consumer_count, "results": results}
    finally:
        builder.close()


@app.post("/graph/filter-values/dynamic")
def graph_filter_values_dynamic(req: GraphExplorerRequest):
    """現在の絞り込み条件を元に、各フィルターの有効な選択肢のみを返す（動的絞り込み用）。"""
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            where, params = _build_explorer_where(req)
            fv: dict[str, Any] = {"consumer": {}}

            # Consumer 属性（絞り込み後の有効値）
            for prop in ["gender", "age_group", "location", "country", "occupation",
                         "income_range", "driving_frequency", "mobility_pattern"]:
                r = session.run(
                    f"MATCH (c:Consumer) {where} "
                    f"WITH DISTINCT c.{prop} AS v WHERE v IS NOT NULL AND v <> '' "
                    f"RETURN v ORDER BY v",
                    **params,
                )
                fv["consumer"][prop] = [row["v"] for row in r]

            # グラフノード（絞り込み後の有効値・拡張オントロジー対応）
            node_queries: dict[str, str] = {
                "decision_style": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_DECISION_STYLE]->(ds:DecisionStyle)
                    RETURN DISTINCT ds.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC
                """,
                "life_event": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:EXPERIENCED]->(le:LifeEvent)
                    RETURN DISTINCT le.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC
                """,
                "trigger": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_TRIGGER]->(t:Trigger)
                    RETURN DISTINCT t.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC
                """,
                "need": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_NEED]->(n:Need)
                    WHERE n.level = 'parent' OR n.level IS NULL
                    RETURN DISTINCT n.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC
                """,
                "sub_need": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_NEED]->(n:Need {{level: 'child'}})
                    RETURN DISTINCT n.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC
                """,
                "evaluation_criteria": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:VALUED]->(ec:EvaluationCriteria)
                    RETURN DISTINCT ec.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC LIMIT 50
                """,
                "purchase_driver": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:DECIDED]->(pd:PurchaseDriver)
                    RETURN DISTINCT pd.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC
                """,
                "regret": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:HAS_REGRET]->(r:Regret)
                    RETURN DISTINCT r.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC
                """,
                "vehicle_model": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:SELECTED]->(v:VehicleModel)
                    RETURN DISTINCT v.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC LIMIT 60
                """,
                "feature": f"""
                    MATCH (c:Consumer) {where}
                    MATCH (c)-[:SELECTED]->(:VehicleModel)-[:HAS_FEATURE]->(f:Feature)
                    RETURN DISTINCT f.name AS name, count(DISTINCT c) AS cnt ORDER BY cnt DESC LIMIT 60
                """,
            }
            for key, query in node_queries.items():
                r = session.run(query, **params)
                fv[key] = [row["name"] for row in r if row["name"]]

            fv["grades_by_vehicle"] = {
                p["model_name"]: p.get("grades", [])
                for p in _load_products()
            }

            return fv
    finally:
        builder.close()


@app.get("/graph/stats")
def graph_stats():
    """グラフ全体の統計情報を返す。"""
    builder = _get_builder()
    try:
        stats = builder.get_stats()
        # VehicleModel のうち製品データあり（Lexus）の数
        with builder.driver.session() as session:
            r = session.run(
                "MATCH (v:VehicleModel) WHERE (v)-[:HAS_FEATURE]->() OR (v)-[:SATISFIES]->() "
                "RETURN count(v) AS lexus_models"
            )
            stats["lexus_models"] = r.single()["lexus_models"]
        return stats
    finally:
        builder.close()


@app.get("/graph/vehicles")
def graph_vehicles():
    """VehicleModel ノード一覧（製品データあり）を返す。"""
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            result = session.run(
                """
                MATCH (v:VehicleModel)
                WHERE (v)-[:HAS_FEATURE]->() OR (v)-[:SATISFIES]->()
                OPTIONAL MATCH (v)-[:SATISFIES]->(n:Need)
                OPTIONAL MATCH (v)-[:HAS_FEATURE]->(f:Feature)
                RETURN v.name AS name,
                       v.category AS category,
                       v.price_range AS price_range,
                       v.fuel_type AS fuel_type,
                       v.seating_capacity AS seating,
                       collect(DISTINCT n.name) AS needs,
                       count(DISTINCT f) AS feature_count
                ORDER BY v.category, v.name
                """
            )
            return {"vehicles": [dict(r) for r in result]}
    finally:
        builder.close()


class CypherRequest(BaseModel):
    query: str
    params: dict = {}


@app.post("/graph/cypher")
def run_cypher(req: CypherRequest):
    """任意の読み取り専用 Cypher クエリを実行する（MATCH / RETURN のみ許可）。"""
    query = req.query.strip()
    # 書き込み系クエリを拒否
    forbidden = ["CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DROP", "CALL db."]
    upper = query.upper()
    for kw in forbidden:
        if kw in upper:
            raise HTTPException(
                status_code=400,
                detail=f"書き込み系クエリは /graph/cypher では使用できません: {kw}",
            )
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            result = session.run(query, **req.params)
            rows = [dict(r) for r in result]
            return {"rows": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        builder.close()


class NodeUpdateRequest(BaseModel):
    node_type: str      # VehicleModel | Need | Feature
    node_name: str
    properties: dict    # 更新するプロパティ


@app.post("/graph/update_node")
def update_node(req: NodeUpdateRequest):
    """ノードのプロパティを更新する（VehicleModel / Need / Feature）。"""
    allowed_types = {"VehicleModel", "Need", "Feature", "Consumer"}
    if req.node_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"node_type は {allowed_types} のみ許可")

    # プロパティのSET句を動的生成
    set_clauses = ", ".join(f"n.{k} = ${k}" for k in req.properties)
    params = {"name": req.node_name, **req.properties}

    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            session.run(
                f"MATCH (n:{req.node_type} {{name: $name}}) SET {set_clauses}",
                **params,
            )
        return {"status": "ok", "message": f"{req.node_type} '{req.node_name}' を更新しました"}
    finally:
        builder.close()


class SatisfiesRequest(BaseModel):
    vehicle_name: str
    need_name: str
    action: str = "add"   # "add" | "remove"


@app.post("/graph/cleanup-orphans")
def graph_cleanup_orphans():
    """Consumer から参照されていない孤立ノード（Trigger / PurchaseDriver / EvaluationCriteria）を削除する。"""
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            deleted = _cleanup_orphan_nodes(session)
        total = sum(deleted.values())
        return {
            "status": "ok",
            "deleted_total": total,
            "deleted": deleted,
            "message": f"孤立ノード {total} 件を削除しました" if total else "削除対象なし",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        builder.close()


@app.post("/graph/satisfies")
def toggle_satisfies(req: SatisfiesRequest):
    """VehicleModel と Need の SATISFIES リレーションを追加または削除する。"""
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            if req.action == "add":
                session.run(
                    """
                    MERGE (n:Need {name: $need})
                    WITH n
                    MATCH (v:VehicleModel {name: $vehicle})
                    MERGE (v)-[:SATISFIES]->(n)
                    """,
                    need=req.need_name, vehicle=req.vehicle_name,
                )
                msg = f"{req.vehicle_name} → SATISFIES → {req.need_name} を追加"
            else:
                session.run(
                    """
                    MATCH (v:VehicleModel {name: $vehicle})-[r:SATISFIES]->(n:Need {name: $need})
                    DELETE r
                    """,
                    need=req.need_name, vehicle=req.vehicle_name,
                )
                msg = f"{req.vehicle_name} → SATISFIES → {req.need_name} を削除"
        return {"status": "ok", "message": msg}
    finally:
        builder.close()


# ── Verification helpers ───────────────────────────────────────────────────

def _load_verification_log() -> list[dict]:
    if VERIFICATION_LOG_PATH.exists():
        return json.loads(VERIFICATION_LOG_PATH.read_text(encoding="utf-8"))
    return []


def _save_verification_log(records: list[dict]) -> None:
    VERIFICATION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    VERIFICATION_LOG_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_stories_map() -> dict[str, dict]:
    if CONSUMER_STORIES_PATH.exists():
        return {s["story_id"]: s
                for s in json.loads(CONSUMER_STORIES_PATH.read_text(encoding="utf-8"))}
    return {}


def _load_decisions_map() -> dict[str, dict]:
    if CONSUMER_DECISIONS_PATH.exists():
        return {d["story_id"]: d
                for d in json.loads(CONSUMER_DECISIONS_PATH.read_text(encoding="utf-8"))}
    return {}


def _cleanup_orphan_nodes(session) -> dict[str, int]:
    """Consumer から参照されなくなった孤立ノードを削除する。
    VehicleModel / Need はプロダクト側でも使われるため対象外。
    """
    deleted: dict[str, int] = {}

    orphan_checks = [
        ("Trigger",         "HAS_TRIGGER"),
        ("PurchaseDriver",  "DECIDED"),
        ("EvaluationCriteria", "VALUED"),
        ("DecisionStyle",   "HAS_DECISION_STYLE"),
        ("LifeEvent",       "EXPERIENCED"),
        ("Regret",          "HAS_REGRET"),
        ("VehicleOwnership","OWNED"),
    ]

    for label, rel in orphan_checks:
        result = session.run(
            f"MATCH (n:{label}) WHERE NOT (()-[:{rel}]->(n)) RETURN count(n) AS n"
        )
        count = result.single()["n"]
        if count > 0:
            session.run(
                f"MATCH (n:{label}) WHERE NOT (()-[:{rel}]->(n)) DETACH DELETE n"
            )
            deleted[label] = count

    return deleted


def _compute_extracted(story: dict, decision: dict) -> dict:
    """graph_builder と同じロジックで抽出値を再現する（検証比較用）。"""
    st_text = story.get("story_text", {}) or {}
    deciding_factor = (st_text.get("deciding_factor", "") if isinstance(st_text, dict) else "")
    if not deciding_factor:
        deciding_factor = story.get("most_satisfied", "")

    kikkake = (story.get("kikkake") or "").strip()

    # Trigger: v2形式ならコードキー、v1ならkikkakeから推定
    trigger_val = decision.get("trigger", "")
    if trigger_val and trigger_val in TRIGGER_LABELS:
        trigger_code = trigger_val
    else:
        trigger_code = _kikkake_to_trigger(kikkake) if kikkake else "other"

    # LifeEvent: v2形式ならコードキー、v1ならkikkakeから推定
    life_event_val = decision.get("life_event")
    if isinstance(life_event_val, str) and life_event_val in LIFE_EVENT_LABELS:
        life_event_code = life_event_val
    else:
        life_event_code = _kikkake_to_life_event(kikkake) if kikkake else None

    # DecisionStyle
    decision_style = decision.get("decision_style", "")

    # PurchaseDriver
    pd_raw = decision.get("purchase_driver", "")
    if not pd_raw:
        pd_raw = deciding_factor
    purchase_driver = _categorize_purchase_driver(pd_raw) if pd_raw else ""

    purchased = (story.get("vehicle_model") or "").strip() or decision.get("selected_vehicle", "").strip()
    all_opts  = list(story.get("considered_options") or decision.get("considered_options") or [])
    competitors = [o.strip() for o in all_opts if o.strip() and o.strip() != purchased]

    return {
        "trigger":          trigger_code,
        "life_event":       life_event_code,
        "decision_style":   decision_style,
        "needs":            decision.get("needs", []),
        "purchase_driver":  [purchase_driver] if purchase_driver else [],
        "selected_vehicle": purchased,
        "grade":            story.get("grade", "").strip(),
        "competitors":      competitors,
        "regret":           decision.get("regret", []),
        "previous_vehicle": decision.get("previous_vehicle"),
    }


# ── Verification endpoints ─────────────────────────────────────────────────

@app.get("/verify/stories")
def verify_stories_list():
    """検証対象ストーリー一覧（未検証 / 検証済 / 要修正）。"""
    stories_map  = _load_stories_map()
    verif_map    = {r["story_id"]: r for r in _load_verification_log()}

    result = []
    for sid, story in stories_map.items():
        rec = verif_map.get(sid)
        if rec is None:
            status = "unverified"
        else:
            has_error = any(
                not f.get("is_correct", True)
                for f in rec.get("fields", {}).values()
            )
            status = "needs_correction" if has_error else "verified"
        result.append({
            "story_id":      sid,
            "title":         story.get("title", ""),
            "vehicle_model": story.get("vehicle_model", ""),
            "kikkake":       story.get("kikkake", ""),
            "post_date":     story.get("post_date", ""),
            "status":        status,
            "verified_at":   rec.get("verified_at", "") if rec else "",
            "applied_at":    rec.get("applied_at", "") if rec else "",
        })

    # 未検証 → 要修正 → 検証済 の順に並べる
    order = {"unverified": 0, "needs_correction": 1, "verified": 2}
    result.sort(key=lambda x: order.get(x["status"], 9))
    return {"stories": result, "total": len(result),
            "verified": sum(1 for r in result if r["status"] != "unverified")}


@app.get("/verify/story/{story_id}")
def verify_story_comparison(story_id: str):
    """元データ vs 抽出結果を並べて返す（検証フォーム用）。"""
    stories_map   = _load_stories_map()
    decisions_map = _load_decisions_map()
    verif_map     = {r["story_id"]: r for r in _load_verification_log()}

    story    = stories_map.get(story_id)
    decision = decisions_map.get(story_id, {})
    if not story:
        raise HTTPException(status_code=404, detail=f"story_id '{story_id}' not found")

    st_text = story.get("story_text", {}) or {}
    extracted = _compute_extracted(story, decision)

    # 元テキスト（フィールドごとに参照元を返す）
    original = {
        "title":             story.get("title", ""),
        "kikkake":           story.get("kikkake", ""),
        "purchase_trigger":  st_text.get("purchase_trigger", "") if isinstance(st_text, dict) else "",
        "purchase_story":    st_text.get("purchase_story",   "") if isinstance(st_text, dict) else "",
        "deciding_factor":   st_text.get("deciding_factor",  "") if isinstance(st_text, dict) else "",
        "advice":            st_text.get("advice",           "") if isinstance(st_text, dict) else "",
        "most_satisfied":    story.get("most_satisfied", ""),
        "vehicle_model":     story.get("vehicle_model", ""),
        "grade":             story.get("grade", ""),
        "considered_options":story.get("considered_options", []),
        "needs_raw":         decision.get("needs", []),
        "satisfaction_score":story.get("satisfaction_score"),
        "age_group":         story.get("age_group", ""),
        "gender":            story.get("gender", ""),
        "location":          story.get("location", ""),
    }

    # 選択車種のグレード一覧（products.json から）
    purchased_name = (story.get("vehicle_model") or "").strip()
    vehicle_grades: list[str] = []
    for _p in _load_products():
        if _p["model_name"].upper() == purchased_name.upper():
            vehicle_grades = _p.get("grades", [])
            break

    # グラフから実値を補完
    all_sub_needs: list[str]     = []
    all_eval_criteria: list[str] = []
    builder = _get_builder()
    try:
        with builder.driver.session() as session:
            r_sn = session.run(
                "MATCH (c:Consumer {id: $cid})-[:HAS_NEED]->(n:Need {level: 'child'}) "
                "RETURN n.name AS name", cid=story_id)
            extracted["sub_need"] = [row["name"] for row in r_sn]

            r_ec = session.run(
                "MATCH (c:Consumer {id: $cid})-[:VALUED]->(ec:EvaluationCriteria) "
                "RETURN ec.name AS name", cid=story_id)
            extracted["evaluation_criteria"] = [row["name"] for row in r_ec]

            # PurchaseDriver をグラフから取得（反映済みなら実値優先）
            r_pd = session.run(
                "MATCH (c:Consumer {id: $cid})-[:DECIDED]->(pd:PurchaseDriver) "
                "RETURN pd.name AS name", cid=story_id)
            pd_from_graph = [row["name"] for row in r_pd]
            if pd_from_graph:
                extracted["purchase_driver"] = pd_from_graph

            # DecisionStyle をグラフから取得
            r_ds = session.run(
                "MATCH (c:Consumer {id: $cid})-[:HAS_DECISION_STYLE]->(ds:DecisionStyle) "
                "RETURN ds.name AS name", cid=story_id)
            ds_from_graph = [row["name"] for row in r_ds]
            if ds_from_graph:
                extracted["decision_style"] = ds_from_graph[0]

            # LifeEvent をグラフから取得
            r_le = session.run(
                "MATCH (c:Consumer {id: $cid})-[:EXPERIENCED]->(le:LifeEvent) "
                "RETURN le.name AS name", cid=story_id)
            le_from_graph = [row["name"] for row in r_le]
            if le_from_graph:
                extracted["life_event"] = le_from_graph[0]

            # Regret をグラフから取得
            r_rg = session.run(
                "MATCH (c:Consumer {id: $cid})-[hr:HAS_REGRET]->(r:Regret) "
                "RETURN r.name AS name, hr.description AS description, hr.severity AS severity",
                cid=story_id)
            regret_from_graph = [
                {"category": row["name"],
                 "description": row["description"] or "",
                 "severity": row["severity"] or 1}
                for row in r_rg
            ]
            if regret_from_graph:
                extracted["regret"] = regret_from_graph

            # 選択肢一覧
            r_all_sn = session.run(
                "MATCH (n:Need {level: 'child'}) RETURN DISTINCT n.name AS name ORDER BY n.name"
            )
            all_sub_needs = [row["name"] for row in r_all_sn]
            r_all_ec = session.run(
                "MATCH (ec:EvaluationCriteria) "
                "RETURN DISTINCT ec.name AS name ORDER BY ec.name LIMIT 100"
            )
            all_eval_criteria = [row["name"] for row in r_all_ec]
    finally:
        builder.close()

    return {
        "story_id":               story_id,
        "original":               original,
        "extracted":              extracted,
        "previous_verification":  verif_map.get(story_id),
        "trigger_categories":     list(TRIGGER_LABELS.keys()),
        "life_event_categories":  list(LIFE_EVENT_LABELS.keys()),
        "decision_style_options": list(DECISION_STYLE_LABELS.keys()),
        "regret_categories":      list(REGRET_CATEGORY_LABELS.keys()),
        "purchase_driver_categories": list(_PURCHASE_DRIVER_CATEGORIES.keys()),
        "vehicle_grades":         vehicle_grades,
        "all_sub_needs":          all_sub_needs,
        "all_eval_criteria":      all_eval_criteria,
        # 後方互換
        "sub_trigger_categories": list(TRIGGER_LABELS.keys()),
    }


@app.post("/verify/story/{story_id}")
def verify_story_submit(story_id: str, record: VerificationRecord):
    """検証結果を保存する。既存レコードは上書き。"""
    records = _load_verification_log()
    # 既存レコードを更新 or 追加
    records = [r for r in records if r["story_id"] != story_id]
    records.append(record.model_dump())
    _save_verification_log(records)
    return {"status": "ok", "story_id": story_id,
            "verified_at": record.verified_at}


@app.get("/verify/stats")
def verify_stats():
    """フィールド別正解率と全体進捗を返す。"""
    stories_map = _load_stories_map()
    records = _load_verification_log()

    total = len(stories_map)
    verified = len(records)
    fields_tracked = ["trigger", "life_event", "decision_style",
                      "needs", "sub_need", "evaluation_criteria",
                      "purchase_driver", "selected_vehicle", "grade",
                      "competitors", "regret"]

    accuracy: dict[str, dict] = {f: {"correct": 0, "incorrect": 0} for f in fields_tracked}
    for rec in records:
        for fname, fdata in rec.get("fields", {}).items():
            if fname in accuracy:
                if fdata.get("is_correct", True):
                    accuracy[fname]["correct"] += 1
                else:
                    accuracy[fname]["incorrect"] += 1

    for fname, counts in accuracy.items():
        total_f = counts["correct"] + counts["incorrect"]
        counts["rate"] = round(counts["correct"] / total_f, 3) if total_f else None

    needs_correction = sum(
        1 for r in records
        if any(not f.get("is_correct", True) for f in r.get("fields", {}).values())
    )

    return {
        "total_stories":       total,
        "verified_count":      verified,
        "needs_correction":    needs_correction,
        "coverage_pct":        round(verified / total * 100, 1) if total else 0,
        "accuracy":            accuracy,
    }


@app.post("/verify/story/{story_id}/apply")
def verify_apply_story(story_id: str):
    """検証ログの訂正内容をNeo4jグラフに反映する（1ストーリー）。"""
    records = _load_verification_log()
    rec = next((r for r in records if r["story_id"] == story_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail=f"'{story_id}' の検証レコードが見つかりません")

    fields = rec.get("fields", {})
    corrections = {
        k: v for k, v in fields.items()
        if not v.get("is_correct", True) and v.get("corrected") is not None
    }
    if not corrections:
        return {"status": "ok", "message": "修正なし（全フィールド正解）", "applied": []}

    builder = _get_builder()
    applied: list[str] = []
    try:
        with builder.driver.session() as session:
            cid = story_id

            # ── trigger ─────────────────────────────────────────────────────
            if "trigger" in corrections:
                corrected = corrections["trigger"].get("corrected")
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:HAS_TRIGGER]->(t:Trigger) "
                    "WHERE t.level IS NULL OR t.level = 'parent' DELETE r",
                    cid=cid)
                if corrected:
                    session.run(
                        "MERGE (t:Trigger {name: $name}) "
                        "WITH t MATCH (c:Consumer {id: $cid}) MERGE (c)-[:HAS_TRIGGER]->(t)",
                        name=corrected, cid=cid)
                applied.append("trigger")

            # ── sub_trigger ─────────────────────────────────────────────────
            if "sub_trigger" in corrections:
                corrected = corrections["sub_trigger"].get("corrected")
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:HAS_TRIGGER]->(t:Trigger {level: 'sub'}) DELETE r",
                    cid=cid)
                if corrected:
                    session.run(
                        "MERGE (st:Trigger {name: $name}) SET st.level = 'sub' "
                        "WITH st MATCH (c:Consumer {id: $cid}) MERGE (c)-[:HAS_TRIGGER]->(st)",
                        name=corrected, cid=cid)
                applied.append("sub_trigger")

            # ── needs (parent) ───────────────────────────────────────────────
            if "needs" in corrections:
                corrected = corrections["needs"].get("corrected") or []
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:HAS_NEED]->(n:Need) "
                    "WHERE n.level = 'parent' OR n.level IS NULL DELETE r",
                    cid=cid)
                for need in corrected:
                    need = need.strip()
                    if need:
                        session.run(
                            "MERGE (n:Need {name: $name}) SET n.level = 'parent' "
                            "WITH n MATCH (c:Consumer {id: $cid}) MERGE (c)-[:HAS_NEED]->(n)",
                            name=need, cid=cid)
                applied.append("needs")

            # ── sub_need (child) ────────────────────────────────────────────
            if "sub_need" in corrections:
                corrected = corrections["sub_need"].get("corrected") or []
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:HAS_NEED]->(n:Need {level: 'child'}) DELETE r",
                    cid=cid)
                for sn in corrected:
                    sn = sn.strip()
                    if sn:
                        session.run(
                            "MERGE (n:Need {name: $name}) SET n.level = 'child' "
                            "WITH n MATCH (c:Consumer {id: $cid}) MERGE (c)-[:HAS_NEED]->(n)",
                            name=sn, cid=cid)
                applied.append("sub_need")

            # ── evaluation_criteria ─────────────────────────────────────────
            if "evaluation_criteria" in corrections:
                corrected = corrections["evaluation_criteria"].get("corrected") or []
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:VALUED]->(ec:EvaluationCriteria) DELETE r",
                    cid=cid)
                for ec in corrected:
                    ec = ec.strip()
                    if ec:
                        session.run(
                            "MERGE (e:EvaluationCriteria {name: $name}) "
                            "WITH e MATCH (c:Consumer {id: $cid}) MERGE (c)-[:VALUED]->(e)",
                            name=ec, cid=cid)
                applied.append("evaluation_criteria")

            # ── purchase_driver（複数対応・リスト or 文字列どちらも受け付ける）───
            if "purchase_driver" in corrections:
                corrected = corrections["purchase_driver"].get("corrected")
                # 後方互換: 文字列ならリスト化、カンマ区切りも分割
                if isinstance(corrected, str):
                    corrected = [p.strip() for p in corrected.split(",") if p.strip()]
                elif not corrected:
                    corrected = []
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:DECIDED]->(pd:PurchaseDriver) DELETE r",
                    cid=cid)
                for pd_name in corrected:
                    pd_name = pd_name.strip()
                    if pd_name:
                        session.run(
                            "MERGE (pd:PurchaseDriver {name: $name}) "
                            "WITH pd MATCH (c:Consumer {id: $cid}) MERGE (c)-[:DECIDED]->(pd)",
                            name=pd_name, cid=cid)
                applied.append("purchase_driver")

            # ── selected_vehicle ────────────────────────────────────────────
            if "selected_vehicle" in corrections:
                corrected = corrections["selected_vehicle"].get("corrected")
                if corrected:
                    existing = session.run(
                        "MATCH (c:Consumer {id: $cid})-[r:SELECTED]->(v) "
                        "RETURN r.satisfaction_score AS score, r.weight AS weight LIMIT 1",
                        cid=cid).single()
                    score  = existing["score"]  if existing else None
                    weight = existing["weight"] if existing else 1.0
                    session.run(
                        "MATCH (c:Consumer {id: $cid})-[r:SELECTED]->() DELETE r",
                        cid=cid)
                    session.run(
                        "MERGE (v:VehicleModel {name: $name}) "
                        "WITH v MATCH (c:Consumer {id: $cid}) "
                        "MERGE (c)-[r:SELECTED]->(v) "
                        "SET r.weight = $weight, r.satisfaction_score = $score",
                        name=corrected, cid=cid,
                        weight=weight if weight is not None else 1.0, score=score)
                    applied.append("selected_vehicle")

            # ── grade ────────────────────────────────────────────────────────
            if "grade" in corrections:
                corrected = corrections["grade"].get("corrected") or ""
                session.run(
                    "MATCH (c:Consumer {id: $cid}) SET c.grade = $grade",
                    cid=cid, grade=corrected)
                applied.append("grade")

            # ── competitors ─────────────────────────────────────────────────
            if "competitors" in corrections:
                corrected = corrections["competitors"].get("corrected") or []
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:CONSIDERED]->() DELETE r",
                    cid=cid)
                sel = session.run(
                    "MATCH (c:Consumer {id: $cid})-[:SELECTED]->(v) RETURN v.name AS name LIMIT 1",
                    cid=cid).single()
                purchased_name = sel["name"] if sel else ""
                for comp_name in corrected:
                    comp_name = comp_name.strip()
                    if comp_name and comp_name != purchased_name:
                        session.run(
                            "MERGE (v:VehicleModel {name: $name}) "
                            "WITH v MATCH (c:Consumer {id: $cid}) MERGE (c)-[:CONSIDERED]->(v)",
                            name=comp_name, cid=cid)
                applied.append("competitors")

            # ── life_event ─────────────────────────────────────────────────
            if "life_event" in corrections:
                corrected = corrections["life_event"].get("corrected")
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:EXPERIENCED]->() DELETE r",
                    cid=cid)
                if corrected and isinstance(corrected, str):
                    session.run(
                        "MERGE (le:LifeEvent {name: $name}) "
                        "SET le.label = $label "
                        "WITH le MATCH (c:Consumer {id: $cid}) MERGE (c)-[:EXPERIENCED]->(le)",
                        name=corrected,
                        label=LIFE_EVENT_LABELS.get(corrected, corrected),
                        cid=cid)
                applied.append("life_event")

            # ── decision_style ──────────────────────────────────────────────
            if "decision_style" in corrections:
                corrected = corrections["decision_style"].get("corrected")
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:HAS_DECISION_STYLE]->() DELETE r",
                    cid=cid)
                if corrected and isinstance(corrected, str):
                    session.run(
                        "MERGE (ds:DecisionStyle {name: $name}) "
                        "SET ds.label = $label, ds.description = $desc "
                        "WITH ds MATCH (c:Consumer {id: $cid}) MERGE (c)-[:HAS_DECISION_STYLE]->(ds)",
                        name=corrected,
                        label=DECISION_STYLE_LABELS.get(corrected, corrected),
                        desc=DECISION_STYLE_DESCRIPTIONS.get(corrected, ""),
                        cid=cid)
                applied.append("decision_style")

            # ── regret ─────────────────────────────────────────────────────
            if "regret" in corrections:
                corrected = corrections["regret"].get("corrected") or []
                session.run(
                    "MATCH (c:Consumer {id: $cid})-[r:HAS_REGRET]->() DELETE r",
                    cid=cid)
                if isinstance(corrected, list):
                    for reg in corrected:
                        if not isinstance(reg, dict):
                            continue
                        cat  = reg.get("category", "other")
                        desc = reg.get("description", "")
                        sev  = reg.get("severity", 1)
                        session.run(
                            "MERGE (r:Regret {name: $name}) "
                            "SET r.label = $label "
                            "WITH r MATCH (c:Consumer {id: $cid}) "
                            "MERGE (c)-[hr:HAS_REGRET]->(r) "
                            "SET hr.description = $desc, hr.severity = $sev",
                            name=cat,
                            label=REGRET_CATEGORY_LABELS.get(cat, cat),
                            desc=desc[:200],
                            sev=int(sev) if sev else 1,
                            cid=cid)
                applied.append("regret")

            # ── 孤立ノードの削除（修正で参照が外れたノードを除去）──────────────
            _cleanup_orphan_nodes(session)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"グラフ反映エラー: {e}")
    finally:
        builder.close()

    # 検証ログに反映日時を記録
    records = _load_verification_log()
    for r in records:
        if r["story_id"] == story_id:
            r["applied_at"]    = datetime.now().isoformat()
            r["applied_fields"] = applied
    _save_verification_log(records)

    return {
        "status": "ok",
        "story_id": story_id,
        "applied": applied,
        "message": f"{len(applied)} フィールドをグラフに反映しました",
    }


@app.post("/verify/apply-all")
def verify_apply_all():
    """要修正ステータスで未反映のストーリーを一括でグラフに反映する。"""
    records = _load_verification_log()
    targets = [
        r for r in records
        if any(not f.get("is_correct", True) for f in r.get("fields", {}).values())
        and not r.get("applied_at")  # 未反映のみ
    ]
    results = []
    for rec in targets:
        try:
            res = verify_apply_story(rec["story_id"])
            results.append({"story_id": rec["story_id"], "status": "ok", "applied": res["applied"]})
        except HTTPException as e:
            results.append({"story_id": rec["story_id"], "status": "error", "error": e.detail})
        except Exception as e:
            results.append({"story_id": rec["story_id"], "status": "error", "error": str(e)})

    applied_count = sum(1 for r in results if r["status"] == "ok")
    return {
        "status": "ok",
        "processed": len(results),
        "applied_count": applied_count,
        "results": results,
    }


@app.post("/admin/re-extract")
def admin_re_extract(sample_size: int = 300):
    """
    consumer_extractor を再実行して consumer_decisions.json を再生成し、
    グラフを再構築する（LLM抽出コストが発生するため管理者操作）。
    """
    import sys, os
    env = {**os.environ, "CONSUMER_SAMPLE_SIZE": str(sample_size)}

    # Step 1: consumer_extractor
    r1 = subprocess.run(
        [sys.executable, "-m", "extractor.consumer_extractor"],
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=600, env=env,
    )
    if r1.returncode != 0:
        raise HTTPException(status_code=500,
                            detail=f"consumer_extractor エラー: {r1.stderr[-500:]}")

    # Step 2: グラフ再構築
    try:
        builder = _get_builder()
        try:
            builder.clear_graph()
            builder.create_constraints()
            builder.load_consumer_decisions()
            builder.load_product_features()
            stats = builder.get_stats()
        finally:
            builder.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"グラフ再構築エラー: {e}")

    return {
        "status":      "ok",
        "sample_size": sample_size,
        "extractor":   r1.stdout[-500:] if r1.stdout else "ok",
        "graph_nodes": stats.get("nodes", {}),
        "graph_rels":  stats.get("relationships", {}),
    }


@app.post("/verify/improvements")
def verify_improvements():
    """誤り訂正レコードをもとに Claude がキーワード改善提案を生成する。"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY が未設定です")

    records = _load_verification_log()
    errors: list[dict] = []
    for rec in records:
        for fname, fdata in rec.get("fields", {}).items():
            if not fdata.get("is_correct", True) and fdata.get("source_text"):
                errors.append({
                    "field":        fname,
                    "story_id":     rec["story_id"],
                    "source_text":  fdata["source_text"][:300],
                    "extracted":    fdata.get("extracted"),
                    "corrected":    fdata.get("corrected"),
                })

    if not errors:
        return {"suggestions": [], "message": "訂正データがまだありません。検証を進めてください。"}

    errors_json = json.dumps(errors[:30], ensure_ascii=False, indent=2)

    prompt = f"""あなたは日本語テキストのキーワード分類ルールを改善するエキスパートです。

以下は、キーワードベースの分類システムが誤った結果を出したケース一覧です。
各ケースには「元テキスト」「誤って抽出されたカテゴリ」「正しいカテゴリ」が含まれます。

【誤分類ケース（最大30件）】
{errors_json}

【フィールド別のカテゴリ辞書構造】
- trigger: {list(TRIGGER_LABELS.keys())}
- life_event: {list(LIFE_EVENT_LABELS.keys())}
- decision_style: {list(DECISION_STYLE_LABELS.keys())}
- purchase_driver: {list(_PURCHASE_DRIVER_CATEGORIES.keys())}

各ケースを分析し、以下の形式でキーワード改善提案を返してください。
「なぜ誤ったか」の分析と「追加すべきキーワード」を具体的に示してください。

以下のJSON形式のみで回答してください（コードブロック不要）:
{{
  "suggestions": [
    {{
      "field": "sub_trigger",
      "correct_category": "車検・乗り換え",
      "wrong_category": "試乗・口コミ",
      "story_ids": ["honda_web_001"],
      "analysis": "元テキストに「車検」があるが、その後に「試乗」も含まれており先にマッチした",
      "add_keywords": ["車検時", "乗り換え時"],
      "reorder_hint": "「車検・乗り換え」を辞書の先頭に近づける"
    }}
  ],
  "summary": "全体的な傾向と優先改善項目の要約"
}}"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)
        return {**data, "error_count": len(errors)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM分析エラー: {e}")


@app.post("/import_product", response_model=ImportProductResponse)
def import_product(req: ImportProductRequest):
    """Legacy: URLから車種情報を抽出してグラフに追加。"""
    try:
        resp = requests.get(req.product_page_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        page_text = soup.get_text(" ", strip=True)[:3000]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = (
        f"以下のWebページから自動車情報をJSONで抽出してください。URL: {req.product_page_url}\n"
        f"{page_text[:2000]}\n\n"
        '出力（JSONのみ）:\n{"model_name":"","category":"SUV","features":[],'
        '"safety_features":[],"technology":[],"specs":{"price_range":"","fuel_type":"","seating_capacity":5}}'
    )
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        product_features = json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"LLM extraction failed: {e}")

    model_name = product_features.get("model_name", "Unknown")
    builder = _get_builder()
    try:
        builder.load_product_features_single(product_features)
    finally:
        builder.close()

    return ImportProductResponse(
        status="ok",
        model_name=model_name,
        message=f"{model_name} をナレッジグラフに追加しました",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.api_server:app", host="0.0.0.0", port=8000, reload=True)
