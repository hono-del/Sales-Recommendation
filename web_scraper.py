"""
Webスキャナー: メーカー公式サイトから車種情報を取得する。

対応モード:
  1. 車種TOP URL モード: 車種トップ + 配下サブページをまとめてスキャン
  2. メーカーTOP URL モード: メーカーページから車種URLを自動検出 → 各車種をスキャン
  3. URLリスト モード: 複数の車種URLを一括スキャン

注意:
  Reactなど JS レンダリングのサイトはHTMLから車種リストを取得できません。
  その場合はサイトマップ解析を試みます。それでも不足する場合は
  「URLリスト一括スキャン」モードをご利用ください。
"""
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

import anthropic
import requests
from bs4 import BeautifulSoup

# Windows コンソールのUTF-8化
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

OUTPUT_PATH = Path("data/raw/products.json")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 車種ページで試みるサブページパターン（末尾スラッシュあり）
VEHICLE_SUBPAGE_PATTERNS = [
    "webcatalog/type/list/",
    "webcatalog/design/",
    "webcatalog/performance/",
    "webcatalog/utility/",
    "webcatalog/relation/",
    "essentials/",
    "spec/",
    "grade/",
    "feature/",
    "safety/",
    "technology/",
    "interior/",
    "exterior/",
]

# Claude に渡すテキストの最大文字数
MAX_TEXT_CHARS = 14000
# 1車種あたり取得する最大ページ数
MAX_PAGES_PER_VEHICLE = 10
# メーカーTOPから検出する最大車種数
MAX_VEHICLES_FROM_MAKER = 25

# ── 非車種パスセグメント（完全一致・大文字小文字無視） ────────────────────────
# ここにあるセグメントは車種名として無視する
_NON_VEHICLE_SEGS: frozenset[str] = frozenset({
    # 汎用自動車用語
    "auto", "autos", "auto-lineup", "auto-archive", "auto-ev", "auto-lineup",
    "car", "cars", "vehicle", "vehicles", "lineup", "catalog", "catalogue",
    "new", "newcar", "used", "usedcar", "ev", "hybrid", "electric", "phev",
    # アクション / リクエスト
    "request", "contact", "inquiry", "apply", "register", "login", "logout",
    "signup", "signin", "mypage", "member", "account", "profile",
    "search", "find", "compare", "estimate", "quote",
    "test", "trial", "testdrive", "test-drive",
    "buy", "purchase", "order", "booking", "reservation", "reserve",
    # ディーラー / サービス
    "dealer", "dealership", "dealerlocator", "showroom", "shop", "store",
    "service", "repair", "maintenance", "parts", "accessories", "option", "options",
    "owner", "manual", "recall", "warranty", "recycle",
    # コーポレート / 情報
    "about", "company", "corporate", "ir", "csr", "esg", "sustainability",
    "recruit", "career", "careers", "jobs", "join", "work",
    "news", "press", "media", "pressroom", "event", "events",
    "campaign", "topics", "info", "blog",
    "history", "heritage", "museum", "brand", "story", "philosophy",
    "innovation", "technology", "research", "development", "openinnovation",
    "racing", "motorsport", "sport", "sportscar",
    # 法的 / ポリシー
    "privacy", "terms", "legal", "cookie", "policy", "disclaimer", "sitemap",
    "help", "faq", "support", "guide", "license",
    # ナビゲーション / ロケーション
    "map", "access", "location", "global", "worldwide",
    # 言語コード
    "en", "jp", "ja", "zh", "ko", "us", "cn", "tw", "th", "id", "vn",
    # 技術 / サイト構造
    "api", "assets", "static", "css", "js", "img", "images", "media",
    "admin", "cms", "error", "404", "403", "500",
    # SNS / シェア
    "sns", "share", "community", "forum",
    # ファイナンス
    "finance", "insurance", "loan", "credit", "fleetsales",
    # 環境 / 安全
    "environment", "ecology", "safety", "mobility", "welfare",
    # メーカー固有（ホンダ）の非車種セクション
    "hondasensing", "hondasensing-elite", "ehev", "hondaon", "hondaconnect",
    "googlebuilt-in", "mobilepowerpack", "mobilityservice",
    "ownersmanual", "manual-access", "monthlyowner", "magazine",
    "gaibukyuden", "green-tax", "ie-oshirase", "linkrequest", "waigaya-base",
    "tabibito", "wearandgoods", "walking-assist", "washer", "monpal",
    "drivers-challenge", "kids", "dreamo", "cubhouse", "hondaon",
    "motor", "motor-lineup", "motor-parts", "motor-recycle", "usedmotor",
    "outdoor", "power", "power-catalog", "power-shopsearch",
    "lawn-garden", "lawnmower", "robot-mower", "tiller", "trimmer",
    "snow", "pump", "jet", "art-garage", "business_services",
    "anti-counterfeit", "trackandfield50th", "uni-cub",
    "regional-mobility-show", "rentacar", "icone",
    "ridersvoice", "usersvoice", "suv",
    # ホンダのバイク（車種名と紛らわしいもの）
    "50-scooter", "gyroe", "gyro", "crf150", "c-card",
    "lite", "supercub110prolite", "crosscub110lite", "supercub110lite",
    # トヨタ固有の非車種セクション
    "gazoo", "gr", "safety-sense", "hybrid-v", "phv",
    # 共通の短縮語・記号など
    "top", "home", "index", "main", "pc", "sp", "mobile",
})

EXTRACT_PROMPT = """以下は自動車メーカー公式サイトの車種ページ（複数ページ）から取得したテキストデータです。
このデータを解析し、この車種の情報を以下のJSON形式で1件にまとめてください。
情報が不明な項目は空文字列または空配列にしてください。

出力形式（JSONのみ・コードブロック不要・配列で1要素）:
[
  {{
    "model_name": "{model_name}",
    "category": "<SUV|SEDAN|MINIVAN|HATCHBACK|COUPE|WAGON|TRUCK|KEI>",
    "features": ["<車種の主要特徴1>", "<特徴2>", "<特徴3>", "<特徴4>"],
    "safety_features": ["<安全機能1>", "<安全機能2>", "<安全機能3>"],
    "technology": ["<先進技術・装備1>", "<技術2>", "<技術3>"],
    "grades": ["<グレード名1>", "<グレード名2>"],
    "specs": {{
      "price_range": "<最低価格〜最高価格（例: 2,530,000〜3,740,000円）>",
      "fuel_type": "<燃料タイプ（ガソリン/ハイブリッド/PHEV/EV）>",
      "seating_capacity": <定員数（整数、不明なら5）>,
      "engine": "<エンジン型式または排気量（例: 1.5L DOHC）>",
      "dimensions": "<全長×全幅×全高 mm（例: 4,675×1,820×1,435mm）>"
    }},
    "target_needs": ["<ニーズ1>", "<ニーズ2>", "<ニーズ3>"]
  }}
]

target_needs は以下から3〜5個選択:
safety, space, fuel_efficiency, comfort, design, technology, family, offroad

取得テキストデータ:
{page_text}"""


# ── ユーティリティ ──────────────────────────────────────────────────────────

def _normalize_url(url: str) -> str:
    """クエリパラメータ・フラグメントを除去して末尾スラッシュを正規化。"""
    p = urlparse(url)
    clean = f"{p.scheme}://{p.netloc}{p.path}"
    return clean.rstrip("/") + "/"


def _is_vehicle_segment(segment: str) -> bool:
    """
    パスセグメントが車種名らしいかどうかを判定する。
    False = 車種名ではない（ナビ、サービス、バイク等）
    """
    if not segment:
        return False
    # 長さチェック（2〜30文字）
    if not (2 <= len(segment) <= 30):
        return False
    # 除外リストに含まれるもの（大文字小文字無視）
    if segment.lower() in _NON_VEHICLE_SEGS:
        return False
    # アルファベットを少なくとも1文字含む
    if not re.search(r"[A-Za-z]", segment):
        return False
    # 使用できる文字: 英数字・ハイフン・コロン・ドット・アンダースコア・プラス
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9\-\.\:\_\+\s]*$", segment):
        return False
    # 純粋な数字だけは除外
    if re.match(r"^\d+$", segment):
        return False
    return True


# ── ページ取得 ──────────────────────────────────────────────────────────────

def fetch_page_text(url: str, timeout: int = 15) -> str | None:
    """URLからページのテキストを取得してクリーニングする。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code in (404, 410):
            return None
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        for tag in soup(["script", "style", "nav", "header", "footer",
                         "meta", "link", "noscript", "iframe", "svg", "img"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(\n.{0,1}){5,}", "\n", text)
        return text.strip() or None
    except requests.exceptions.HTTPError:
        return None
    except Exception as e:
        print(f"  [WARN] fetch_page_text({url}): {e}")
        return None


# ── 車種サブページ検出 ──────────────────────────────────────────────────────

def discover_vehicle_pages(top_url: str) -> list[str]:
    """
    車種TOPページをスキャンし、関連サブページのURLリストを返す。
    1. TOPページのリンクから同一パス配下のURLを収集
    2. 固定パターン（webcatalog/type/list/ など）を追加試行
    """
    top_url = _normalize_url(top_url)
    found: list[str] = [top_url]
    seen: set[str] = {top_url}

    try:
        resp = requests.get(top_url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        skip_kw = ["#", "javascript:", "mailto:", "tel:", "contact", "dealer",
                   "login", "register", "privacy", "terms", "sitemap"]

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or any(s in href.lower() for s in skip_kw):
                continue
            full = _normalize_url(urljoin(top_url, href))
            if full.startswith(top_url) and full != top_url and full not in seen:
                seen.add(full)
                found.append(full)

    except Exception as e:
        print(f"  [WARN] discover_vehicle_pages({top_url}): {e}")

    # 固定パターンも追加（ページにリンクがなくても試行）
    for pattern in VEHICLE_SUBPAGE_PATTERNS:
        candidate = top_url + pattern
        if candidate not in seen:
            seen.add(candidate)
            found.append(candidate)

    return found[:MAX_PAGES_PER_VEHICLE]


# ── メーカーTOPからの車種URL検出（多戦略） ───────────────────────────────────

def discover_vehicles_from_maker(maker_url: str) -> list[dict]:
    """
    メーカーTOPページをスキャンし、車種ページと推定されるURLと車種名のリストを返す。
    返却形式: [{"model_name": "INSIGHT", "url": "https://..."}]

    戦略:
      1. HTMLリンク抽出: ページ内のaタグからドメイン直下 + メーカーパス配下の両方を検索
      2. サイトマップXML解析: sitemap.xml / robots.txt 経由でサイトマップを取得
    """
    p = urlparse(maker_url)
    base_domain = f"{p.scheme}://{p.netloc}"
    maker_path = p.path.rstrip("/")   # 例: "" or "/auto"

    # url → model_name のマップ（dedup用）
    vehicle_map: dict[str, str] = {}

    # 戦略1: HTMLリンク抽出
    _html_strategy(maker_url, p, base_domain, maker_path, vehicle_map)
    print(f"  [discover] HTML strategy: {len(vehicle_map)} candidate(s)")

    # 戦略2: サイトマップXML
    _sitemap_strategy(base_domain, maker_path, vehicle_map)
    print(f"  [discover] After sitemap: {len(vehicle_map)} candidate(s)")

    result = [
        {"model_name": name, "url": url}
        for url, name in vehicle_map.items()
    ]
    return result[:MAX_VEHICLES_FROM_MAKER]


def _html_strategy(
    maker_url: str,
    parsed,
    base_domain: str,
    maker_path: str,
    vehicle_map: dict,
) -> None:
    """HTMLページのリンクから車種URLを抽出する。"""
    try:
        resp = requests.get(maker_url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            full = urljoin(maker_url, href)
            lp = urlparse(full)

            # 同一ドメインのみ
            if lp.netloc != parsed.netloc:
                continue

            link_path = lp.path
            path_parts = [pp for pp in link_path.strip("/").split("/") if pp]
            if not path_parts:
                continue

            segment: str | None = None

            # パターンA: ドメイン直下の1セグメント  /INSIGHT/ /N-BOX/ など
            if len(path_parts) == 1:
                segment = path_parts[0]

            # パターンB: maker_path の直下1セグメント  /auto/INSIGHT/ など
            elif maker_path and link_path.startswith(maker_path + "/"):
                rest_parts = [
                    pp for pp in link_path[len(maker_path):].strip("/").split("/") if pp
                ]
                if len(rest_parts) == 1:
                    segment = rest_parts[0]

            if segment and _is_vehicle_segment(segment):
                # ベースURLを構築（サブページを含まない）
                base_seg = path_parts[0]  # ドメイン直下セグメントを使用
                vehicle_url = f"{base_domain}/{base_seg}/"
                if vehicle_url not in vehicle_map:
                    vehicle_map[vehicle_url] = segment.upper()

    except Exception as e:
        print(f"  [WARN] _html_strategy: {e}")


def _sitemap_strategy(
    base_domain: str,
    maker_path: str,
    vehicle_map: dict,
) -> None:
    """
    サイトマップXMLを解析して車種URLを検出する。
    robots.txt からサイトマップURLを取得し、サイトマップインデックスにも対応。
    """
    # サイトマップURL候補リスト（robots.txtを優先）
    sitemap_candidates: list[str] = []

    try:
        robots_resp = requests.get(
            f"{base_domain}/robots.txt", headers=HEADERS, timeout=10
        )
        if robots_resp.ok:
            for line in robots_resp.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    url = line.split(":", 1)[1].strip()
                    if url and url not in sitemap_candidates:
                        sitemap_candidates.append(url)
    except Exception:
        pass

    # フォールバック候補
    for path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemapxml/sitemap.xml",
                 "/sitemap/sitemap.xml"]:
        cand = base_domain + path
        if cand not in sitemap_candidates:
            sitemap_candidates.append(cand)

    for sitemap_url in sitemap_candidates[:5]:
        try:
            resp = requests.get(sitemap_url, headers=HEADERS, timeout=15)
            if not resp.ok:
                continue

            root = ET.fromstring(resp.content)
            # XML名前空間（あり・なし両対応）
            ns_sm = "http://www.sitemaps.org/schemas/sitemap/0.9"
            ns = {"sm": ns_sm}

            # サイトマップインデックス（<sitemapindex>）か通常サイトマップ（<urlset>）か判定
            tag_local = root.tag.split("}")[-1] if "}" in root.tag else root.tag

            if tag_local == "sitemapindex":
                # インデックス → 子サイトマップを再帰処理
                for loc_el in root.findall(f".//{{{ns_sm}}}loc"):
                    child_url = (loc_el.text or "").strip()
                    if child_url:
                        _parse_sitemap_locs(child_url, base_domain, maker_path, vehicle_map)
                        if len(vehicle_map) >= MAX_VEHICLES_FROM_MAKER:
                            break
            else:
                # 通常サイトマップ
                _extract_vehicles_from_root(root, base_domain, maker_path, vehicle_map, ns_sm)

            if len(vehicle_map) >= 3:
                break  # 十分見つかれば終了

        except ET.ParseError:
            pass  # XMLパースエラーは無視
        except Exception as e:
            print(f"  [WARN] sitemap {sitemap_url}: {e}")


def _parse_sitemap_locs(
    sitemap_url: str,
    base_domain: str,
    maker_path: str,
    vehicle_map: dict,
) -> None:
    """子サイトマップURLを取得してloc要素を処理する。"""
    try:
        resp = requests.get(sitemap_url, headers=HEADERS, timeout=15)
        if not resp.ok:
            return
        root = ET.fromstring(resp.content)
        ns_sm = "http://www.sitemaps.org/schemas/sitemap/0.9"
        _extract_vehicles_from_root(root, base_domain, maker_path, vehicle_map, ns_sm)
    except Exception as e:
        print(f"  [WARN] _parse_sitemap_locs({sitemap_url}): {e}")


def _extract_vehicles_from_root(
    root: ET.Element,
    base_domain: str,
    maker_path: str,
    vehicle_map: dict,
    ns_sm: str,
) -> None:
    """ET.ElementのURLsetから車種URLを抽出する。"""
    for loc_el in root.iter(f"{{{ns_sm}}}loc"):
        url = (loc_el.text or "").strip()
        if not url.startswith(base_domain):
            continue

        link_path = urlparse(url).path
        path_parts = [pp for pp in link_path.strip("/").split("/") if pp]
        if not path_parts:
            continue

        segment: str | None = None
        base_seg: str | None = None

        # ドメイン直下1セグメント: /INSIGHT/ → OK
        # ドメイン直下1セグメント + サブパス: /N-ONE-e/new/ → 先頭を取得
        if not maker_path or not link_path.startswith(maker_path + "/"):
            # ドメイン直下パターン
            if len(path_parts) >= 1:
                segment = path_parts[0]
                base_seg = path_parts[0]
        else:
            # maker_path 配下: /auto/INSIGHT/
            rest_parts = [
                pp for pp in link_path[len(maker_path):].strip("/").split("/") if pp
            ]
            if rest_parts:
                segment = rest_parts[0]
                base_seg = f"{maker_path.strip('/')}/{rest_parts[0]}"

        if segment and base_seg and _is_vehicle_segment(segment):
            vehicle_url = f"{base_domain}/{base_seg.strip('/')}/"
            if vehicle_url not in vehicle_map:
                vehicle_map[vehicle_url] = segment.upper()


# ── Claude による情報抽出 ─────────────────────────────────────────────────────

def extract_from_url(
    model_name: str,
    top_url: str,
    client: anthropic.Anthropic,
) -> dict | None:
    """車種TOPのURLから複数ページをスキャンし、Claude で構造化データを抽出する。"""
    print(f"\n  [{model_name}] Discovering pages from {top_url}")
    pages = discover_vehicle_pages(top_url)
    print(f"  [{model_name}] {len(pages)} page(s) to try")

    combined_parts: list[str] = []
    fetched = 0
    for url in pages:
        text = fetch_page_text(url)
        if not text:
            continue
        combined_parts.append(f"=== {url} ===\n{text[:3000]}")
        fetched += 1
        time.sleep(0.8)
        if sum(len(pp) for pp in combined_parts) >= MAX_TEXT_CHARS:
            break

    if not combined_parts:
        print(f"  [{model_name}] No content fetched")
        return None

    combined_text = "\n\n".join(combined_parts)[:MAX_TEXT_CHARS]
    print(f"  [{model_name}] Fetched {fetched} page(s), {len(combined_text)} chars → Claude")

    prompt = EXTRACT_PROMPT.format(
        model_name=model_name,
        page_text=combined_text,
    )

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"  [{model_name}] Rate limit — waiting {wait}s (attempt {attempt+1}/3)")
            time.sleep(wait)
        except Exception as e:
            print(f"  [{model_name}] API error: {e}")
            return None
    else:
        print(f"  [{model_name}] All retries failed")
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
        result["source"] = "web"
        result["source_url"] = top_url
        price = result.get("specs", {}).get("price_range", "?")
        print(f"  [{model_name}] OK — {result.get('category','?')} — {price}")
        return result

    except (json.JSONDecodeError, ValueError) as e:
        print(f"  [{model_name}] JSON parse failed: {e}")
        print(f"  Raw: {raw[:400]}")
        return None


# ── products.json へのマージ ─────────────────────────────────────────────────

def merge_product(new_product: dict) -> None:
    """products.json に新しい車種データをマージ（同名モデルは上書き）。"""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    model_key = new_product.get("model_name", "").upper()
    existing = [p for p in existing if p.get("model_name", "").upper() != model_key]
    existing.append(new_product)

    OUTPUT_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  Saved → {OUTPUT_PATH} ({len(existing)} models total)")


# ── グラフ更新ステップ ────────────────────────────────────────────────────────

def _run_graph_update() -> dict[str, str]:
    """product_extractor を実行してグラフを更新する。"""
    import subprocess
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    r = subprocess.run(
        ["python", "-m", "extractor.product_extractor"],
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=120, env=env,
    )
    return {"extractor": "ok" if r.returncode == 0 else f"error: {r.stderr[-300:]}"}


# ── 高レベルAPI（api_server.py から呼ぶ） ────────────────────────────────────

def scan_vehicle_url(model_name: str, url: str, update_graph: bool = True) -> dict:
    """単一車種URLをスキャンして products.json を更新する。"""
    if not ANTHROPIC_API_KEY:
        return {"status": "error", "message": "ANTHROPIC_API_KEY が設定されていません"}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    result = extract_from_url(model_name, url, client)

    if not result:
        return {"status": "error", "message": f"{model_name} のデータ取得に失敗しました"}

    merge_product(result)

    graph_steps: dict[str, str] = {}
    if update_graph:
        graph_steps = _run_graph_update()

    return {
        "status": "ok",
        "model_name": result["model_name"],
        "category": result.get("category", ""),
        "grades": result.get("grades", []),
        "price_range": result.get("specs", {}).get("price_range", ""),
        "graph_steps": graph_steps,
    }


def scan_url_list(
    vehicles: list[dict],
    update_graph: bool = True,
) -> dict:
    """
    複数の車種URLを一括スキャンする。
    vehicles: [{"model_name": "INSIGHT", "url": "https://..."}, ...]
    """
    if not ANTHROPIC_API_KEY:
        return {"status": "error", "message": "ANTHROPIC_API_KEY が設定されていません"}
    if not vehicles:
        return {"status": "error", "message": "URLリストが空です"}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    succeeded: list[str] = []
    failed: list[str] = []

    for v in vehicles:
        model_name = v.get("model_name", "").strip().upper() or "UNKNOWN"
        url = v.get("url", "").strip()
        if not url:
            failed.append(model_name)
            continue
        result = extract_from_url(model_name, url, client)
        if result:
            merge_product(result)
            succeeded.append(result["model_name"])
        else:
            failed.append(model_name)
        time.sleep(2)

    graph_steps: dict[str, str] = {}
    if update_graph and succeeded:
        graph_steps = _run_graph_update()

    return {
        "status": "ok" if succeeded else "error",
        "succeeded": succeeded,
        "failed": failed,
        "count": len(succeeded),
        "graph_steps": graph_steps,
    }


def scan_maker_url(
    maker_url: str,
    max_vehicles: int = 10,
    update_graph: bool = True,
) -> dict:
    """メーカーTOPからすべての車種をスキャンして products.json を更新する。"""
    if not ANTHROPIC_API_KEY:
        return {"status": "error", "message": "ANTHROPIC_API_KEY が設定されていません"}

    vehicles = discover_vehicles_from_maker(maker_url)
    if not vehicles:
        return {
            "status": "error",
            "message": (
                "車種ページが見つかりませんでした。"
                "JSレンダリングのサイトの場合は「URLリスト一括スキャン」をご利用ください。"
            ),
        }

    return scan_url_list(vehicles[:max_vehicles], update_graph=update_graph)
