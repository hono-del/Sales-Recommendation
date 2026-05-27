"""
Phase 1: Honda family meeting stories scraper
- 新着 / 車種別 / きっかけ別 / 福祉車両 対応
- 各ページから詳細フィールドを抽出
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Windows コンソールのUTF-8化
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_URL   = "https://www.honda.co.jp/familymeeting/"
OUTPUT_PATH = Path("data/raw/consumer_stories.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9",
}

# Honda 公式サイトのURL → 車種名マッピング
CAR_URL_TO_MODEL: dict[str, str] = {
    "/fit/":            "FIT",        "/Fit/":         "FIT",
    "/freed/":          "フリード",    "/FREED/":       "フリード",
    "/stepwgn/":        "ステップワゴン", "/StepWGN/":  "ステップワゴン",
    "/odyssey/":        "オデッセイ",  "/Odyssey/":     "オデッセイ",
    "/cr-v/":           "CR-V",        "/CR-V/":        "CR-V",
    "/vezel/":          "VEZEL",       "/VEZEL/":       "VEZEL",
    "/zr-v/":           "ZR-V",        "/ZR-V/":        "ZR-V",
    "/civic/":          "CIVIC",       "/Civic/":       "CIVIC",
    "/civic-r/":        "CIVIC TYPE R", "/civichatchback/": "CIVIC",
    "/accord/":         "ACCORD",      "/Accord/":      "ACCORD",
    "/insight/":        "インサイト",  "/Insight/":     "インサイト",
    "/n-box/":          "N-BOX",       "/nbox/":        "N-BOX", "/N-BOX/":  "N-BOX",
    "/n-one/":          "N-ONE",       "/N-ONE/":       "N-ONE",
    "/n-wgn/":          "N-WGN",       "/N-WGN/":       "N-WGN",
    "/n-van/":          "N-VAN",       "/N-VAN/":       "N-VAN",
    "/s660/":           "S660",        "/S660/":        "S660",
    "/nsx/":            "NSX",         "/NSX/":         "NSX",
    "/legend/":         "LEGEND",      "/Legend/":      "LEGEND",
    "/shuttle/":        "SHUTTLE",     "/Shuttle/":     "SHUTTLE",
    "/grace/":          "GRACE",       "/Grace/":       "GRACE",
    "/jade/":           "ジェイド",
    "/clarityphev/":    "CLARITY",     "/Clarity/":     "CLARITY",
    "/honda-e/":        "Honda e",
    "/acty-truck/":     "ACTY TRUCK",
    "/stream/":         "ストリーム",
    "/elysion/":        "エリシオン",
    "/mobilio/":        "モビリオ",
    "/cr-x/":           "CR-X",
    "/fitshuttle/":     "フィットシャトル",
    "/crossroad/":      "クロスロード",
    "/edix/":           "エディックス",
    "/integra/":        "インテグラ",
    "/airwave/":        "エアウェイブ",
    "/life/":           "ライフ",
    "/zest/":           "ゼスト",
    "/that-s/":         "That's",
}

# ─────────────────────────────────────────────────────────────
# HTML取得
# ─────────────────────────────────────────────────────────────

def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    enc = resp.apparent_encoding or "utf-8"
    enc_n = enc.lower().replace("-", "_")
    if enc_n in ("shift_jis", "sjis", "s_jis", "ms932", "cp932"):
        enc = "shift_jis"
    elif enc_n in ("euc_jp", "eucjp"):
        enc = "euc-jp"
    return BeautifulSoup(resp.content, "html.parser", from_encoding=enc)


# ─────────────────────────────────────────────────────────────
# URL分類: 詳細ページ vs 一覧ページ
# ─────────────────────────────────────────────────────────────

def is_detail_url(url: str) -> bool:
    """
    詳細ページのURLパターン判定。
      新着:   /familymeeting/new/{6-8桁日付}/NNN.html
      車種別: /familymeeting/{model}/YYYY/NNN/index.html
      福祉:   /familymeeting/welfare-voice/YYYY/NNN.html
    """
    path = urlparse(url).path
    if "/familymeeting/" not in path:
        return False
    # 新着
    if re.search(r"/familymeeting/new/\d{6,8}/\d{3}\.html$", path):
        return True
    # 車種別 (YYYY/NNN/index.html)
    if re.search(r"/familymeeting/[\w-]+/\d{4}/\d{3}/index\.html$", path):
        return True
    # 福祉車両 (YYYY/NNN.html)
    if re.search(r"/familymeeting/welfare-voice/\d{4}/\d{3}\.html$", path):
        return True
    return False


# ─────────────────────────────────────────────────────────────
# 一覧ページから詳細URLを収集
# ─────────────────────────────────────────────────────────────

def collect_detail_links_from_page(soup: BeautifulSoup, page_url: str) -> list[str]:
    """一覧ページ（soup）から詳細ページURLを抽出する。"""
    links: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript"):
            continue
        full = urljoin(page_url, href)
        if is_detail_url(full) and full not in seen:
            seen.add(full)
            links.append(full)
    return links


def collect_list_page_links(soup: BeautifulSoup, page_url: str) -> list[str]:
    """
    一覧ページ自体の次ページURLを返す（ページネーション対応）。
    例: 002.html, 003.html など
    """
    base_path = urlparse(page_url).path
    base_dir  = base_path.rsplit("/", 1)[0] + "/"
    pages: list[str] = []
    seen: set[str] = set([page_url])
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(page_url, href)
        path = urlparse(full).path
        # 同じディレクトリの NNN.html（数字3桁）かつ index.html でないもの
        if (path.startswith(base_dir)
                and re.search(r"/\d{2,3}\.html$", path)
                and not path.endswith("index.html")
                and full not in seen):
            seen.add(full)
            pages.append(full)
    return pages


# ─────────────────────────────────────────────────────────────
# セクション別に一覧→詳細リンクを全ページ収集
# ─────────────────────────────────────────────────────────────

# スクレイプ対象トップインデックス
TOP_INDEXES = [
    "https://www.honda.co.jp/familymeeting/new/",
    "https://www.honda.co.jp/familymeeting/select/",
    "https://www.honda.co.jp/familymeeting/kikkake/",
    "https://www.honda.co.jp/familymeeting/welfare-voice/",
    "https://www.honda.co.jp/familymeeting/",
]


def crawl_all_detail_links(
    pages_per_model: int = 3,   # モデル一覧を最大何ページ読むか
    max_total: int = 150,       # 詳細URL合計上限
) -> list[str]:
    """
    全セクションから詳細ページURLを収集する。PoC用に上限あり。
    """
    all_detail: list[str]  = []
    detail_seen: set[str]  = set()
    index_visited: set[str] = set()

    def add_details(soup: BeautifulSoup, page_url: str):
        """soup から詳細URLを all_detail に追加。"""
        for lnk in collect_detail_links_from_page(soup, page_url):
            if lnk not in detail_seen and len(all_detail) < max_total:
                detail_seen.add(lnk)
                all_detail.append(lnk)

    def scrape_model_section(section_url: str):
        """
        /familymeeting/{model}/ 配下を pages_per_model ページまで処理。
        ページネーションは線形に（再帰しない）。
        """
        if len(all_detail) >= max_total:
            return
        if section_url in index_visited:
            return
        index_visited.add(section_url)

        try:
            print(f"  [MODEL] {section_url}")
            soup = fetch_soup(section_url)
        except Exception as e:
            print(f"  [WARN] {section_url}: {e}")
            return
        time.sleep(0.4)

        add_details(soup, section_url)

        # 最初のリスト一覧ページ (001.html) を取得してから pages_per_model 件
        # 一覧ページを線形に辿る（再帰しない）
        list_pages = collect_list_page_links(soup, section_url)
        for lp in list_pages[:pages_per_model]:
            if len(all_detail) >= max_total:
                break
            if lp in index_visited:
                continue
            index_visited.add(lp)
            try:
                print(f"    [PAGE] {lp}")
                sp2 = fetch_soup(lp)
                add_details(sp2, lp)
            except Exception as e:
                print(f"    [WARN] {lp}: {e}")
            time.sleep(0.4)

    def scrape_top_index(top_url: str):
        """トップインデックス（/new/, /select/, /kikkake/, /welfare-voice/）を処理。"""
        if len(all_detail) >= max_total:
            return
        if top_url in index_visited:
            return
        index_visited.add(top_url)

        try:
            print(f"\n[INDEX] {top_url}")
            soup = fetch_soup(top_url)
        except Exception as e:
            print(f"[WARN] {top_url}: {e}")
            return
        time.sleep(0.4)

        # 直接詳細リンクがあれば収集
        add_details(soup, top_url)

        # モデル別・きっかけ別サブセクションを探して処理
        for a in soup.find_all("a", href=True):
            if len(all_detail) >= max_total:
                break
            href = a["href"].strip()
            full = urljoin(top_url, href)
            path = urlparse(full).path
            if "familymeeting" not in path:
                continue
            if full in index_visited:
                continue
            # サブセクション index（末尾 / または model/）
            if path.endswith("/") and not is_detail_url(full):
                scrape_model_section(full)
            # きっかけ別 NN/01.html
            elif re.search(r"/kikkake/\d+/01\.html$", path):
                if full not in index_visited:
                    index_visited.add(full)
                    try:
                        print(f"  [KIKKAKE] {full}")
                        sp = fetch_soup(full)
                        add_details(sp, full)
                    except Exception:
                        pass
                    time.sleep(0.4)

    for top in TOP_INDEXES:
        if len(all_detail) < max_total:
            scrape_top_index(top)

    return all_detail


# ─────────────────────────────────────────────────────────────
# 車種名解決
# ─────────────────────────────────────────────────────────────

def resolve_vehicle_model(url: str, soup: BeautifulSoup) -> str:
    """
    優先順位:
    1. URL パス中の車種セグメント
    2. foot-btn「このクルマの情報ページへ」のhref
    3. rightColumn img alt (モデル名っぽい場合)
    """
    path = urlparse(url).path.lower()

    # 1) URL path
    for key, model in CAR_URL_TO_MODEL.items():
        if key.lower() in path:
            return model

    # 2) foot-btn リンク
    for a in soup.select(".foot-btn a"):
        if "情報ページ" in a.get_text():
            href = a.get("href", "")
            for key, model in CAR_URL_TO_MODEL.items():
                if key.lower() == href.lower().rstrip("/") + "/":
                    return model
            # href が "/Fit/" のような場合: 正規化して探す
            norm = "/" + href.strip("/").split("/")[-1].lower() + "/"
            for key, model in CAR_URL_TO_MODEL.items():
                if key.lower() == norm:
                    return model
            # フォールバック: href のパスセグメントをそのまま大文字化
            seg = href.strip("/").split("/")[-1]
            if seg:
                return seg.upper()

    # 3) rightColumn img alt
    rc = soup.find(id="rightColumn")
    if rc:
        img = rc.find("img")
        if img:
            alt = img.get("alt", "").strip()
            # alt がモデル名っぽい (短い & 日本語 or 英数字のみ)
            if alt and len(alt) <= 20 and not any(c in alt for c in ["、", "！", "。", "？"]):
                return alt

    # welfare-voice URL ならデフォルト
    if "welfare-voice" in path:
        return "Honda 福祉車両"

    return "Honda Vehicle"


# ─────────────────────────────────────────────────────────────
# 詳細ページのスクレイピング
# ─────────────────────────────────────────────────────────────

def scrape_detail(url: str, story_id: str) -> dict | None:
    """
    詳細ページから全フィールドを抽出。
    返すスキーマ:
    {
      story_id, title,
      gender, age_group, location,
      grade, post_date,
      vehicle_model,
      kikkake, most_satisfied, satisfaction_score,
      story_text: {
        purchase_trigger, purchase_story, deciding_factor, advice
      },
      considered_options
    }
    """
    try:
        soup = fetch_soup(url)
    except Exception as e:
        print(f"    [WARN] fetch failed {url}: {e}")
        return None

    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    # ── leftColumn ──────────────────────────────────────────────────────
    lc = soup.find(id="leftColumn")
    if not lc:
        return None  # 詳細ページではない

    # タイトル
    h3 = lc.find("h3")
    title = h3.get_text(strip=True) if h3 else ""

    # プロフィール行: "男性／50代／埼玉県"
    # <p> が未閉じのため decode_contents だと grade/span が混入する。
    # <br> 直後の NavigableString のみを取得して安全に分解する。
    gender = age_group = location = ""
    for p in lc.find_all("p"):
        br = p.find("br")
        if not br:
            continue
        # <br> の直後にある NavigableString だけを結合（Tagはスキップ）
        raw_text = ""
        for node in br.next_siblings:
            if isinstance(node, str):
                raw_text += node
            else:
                break   # <p> や <span> に達したら終了
        profile_line = raw_text.strip().strip("（）()")
        segs = [s.strip() for s in profile_line.split("／") if s.strip()]
        if not segs:
            continue
        gender    = segs[0] if len(segs) > 0 else ""
        age_group = segs[1] if len(segs) > 1 else ""
        # location: 都道府県名だけを正規表現で切り出す（後ろにgradeが混入しても安全）
        raw_loc = segs[2] if len(segs) > 2 else ""
        m = re.match(r"(.{2,8}?[都道府県市区町村])", raw_loc)
        location = m.group(1) if m else raw_loc[:6]
        break

    # グレード・日付: <span>グレード<br>日付</span>
    grade = post_date = ""
    span = lc.find("span")
    if span:
        raw_span = span.decode_contents()
        sp = re.split(r"<br\s*/?>", raw_span, flags=re.I)
        if sp:
            grade     = BeautifulSoup(sp[0], "html.parser").get_text(strip=True)
        if len(sp) >= 2:
            post_date = BeautifulSoup(sp[1], "html.parser").get_text(strip=True)

    # ── centerColumn ────────────────────────────────────────────────────
    cc = soup.find(id="centerColumn")
    kikkake = most_satisfied = ""
    satisfaction_score = 0

    if cc:
        for td in cc.find_all("td", class_="text"):
            raw = td.decode_contents()
            text = td.get_text(" ", strip=True)
            if "きっかけ：" in text:
                sp = re.split(r"<br\s*/?>", raw, flags=re.I)
                if len(sp) >= 2:
                    kikkake = BeautifulSoup(sp[-1], "html.parser").get_text(strip=True)
            elif "最も満足しているのは：" in text:
                sp = re.split(r"<br\s*/?>", raw, flags=re.I)
                if len(sp) >= 2:
                    most_satisfied = BeautifulSoup(sp[-1], "html.parser").get_text(strip=True)

        # 総合満足度: <img alt="満足度5">
        sat_img = cc.find("img", alt=re.compile(r"^満足度\d$"))
        if sat_img:
            m = re.search(r"(\d)", sat_img["alt"])
            if m:
                satisfaction_score = int(m.group(1))

    # ── vehicle_model ────────────────────────────────────────────────────
    vehicle_model = resolve_vehicle_model(url, soup)

    # ── story_text (4セクション dt/dd) ──────────────────────────────────
    section_keys = {
        "クルマのご購入を考えたきっかけ":      "purchase_trigger",
        "ご購入までのエピソード・ストーリー":   "purchase_story",
        "何が購入の決め手になりましたか？":     "deciding_factor",
        "同じクルマを検討している人へアドバイス！": "advice",
    }
    story_text: dict[str, str] = {v: "" for v in section_keys.values()}

    for dt in soup.find_all("dt"):
        dt_text = dt.get_text(strip=True)
        key = section_keys.get(dt_text)
        if key:
            dd = dt.find_next_sibling("dd")
            if dd:
                story_text[key] = dd.get_text(" ", strip=True)

    # ── considered_options ──────────────────────────────────────────────
    considered: list[str] = []
    for div in soup.find_all("div", class_="roundFrame"):
        for a in div.find_all("a", href=True):
            t = a.get_text(strip=True)
            if t:
                considered.append(t)

    return {
        "story_id":           story_id,
        "title":              title,
        "gender":             gender,
        "age_group":          age_group,
        "location":           location,
        "grade":              grade,
        "post_date":          post_date,
        "vehicle_model":      vehicle_model,
        "kikkake":            kikkake,
        "most_satisfied":     most_satisfied,
        "satisfaction_score": satisfaction_score,
        "story_text": {
            "purchase_trigger": story_text["purchase_trigger"],
            "purchase_story":   story_text["purchase_story"],
            "deciding_factor":  story_text["deciding_factor"],
            "advice":           story_text["advice"],
        },
        "considered_options": considered,
    }


# ─────────────────────────────────────────────────────────────
# フォールバックストーリー生成
# ─────────────────────────────────────────────────────────────

def generate_fallback_stories(count: int) -> list[dict]:
    templates = [
        ("子どもが生まれてフリードに乗り換えました", "フリード", "女性", "30代", "東京都",
         "フリード e:HEV HOME", "子どもの誕生",
         "第一子が生まれることになり手狭になった", "チャイルドシート設置のしやすさ",
         {"purchase_trigger": "第一子が生まれ、コンパクトカーでは荷物が入らなくなりました。",
          "purchase_story":   "ホンダのショールームで試乗し、スライドドアの便利さに感動しました。",
          "deciding_factor":  "使い勝手の良さと価格のバランスが決め手でした。",
          "advice":           "子育て中のファミリーに自信を持っておすすめできます。"}, 4),
        ("家族が増えてステップワゴンを選びました", "ステップワゴン", "男性", "40代", "神奈川県",
         "ステップワゴン SPADA", "三人目の子どもの誕生",
         "3人目の子どもが生まれ7人乗りが必要になった", "広い室内空間",
         {"purchase_trigger": "三人目の子どもが生まれ、7人乗りのミニバンを探しました。",
          "purchase_story":   "わくわくゲートの使いやすさが試乗で確認できました。",
          "deciding_factor":  "両側スライドドアと後席シートアレンジの自由度が決め手でした。",
          "advice":           "大家族には最高の一台です。安全性能も充実しています。"}, 5),
        ("アウトドアが好きでCR-Vにしました", "CR-V", "男性", "30代", "長野県",
         "CR-V e:HEV", "趣味のアウトドア",
         "キャンプ道具が増え積載量のある車が必要になった", "走行性能",
         {"purchase_trigger": "キャンプや登山が趣味で、荷物をたくさん積めるSUVを探していました。",
          "purchase_story":   "四駆性能と荷室の広さを複数車種と比較しました。",
          "deciding_factor":  "ハイブリッドシステムの燃費と走破性のバランスが最高でした。",
          "advice":           "アウトドア好きには最適な一台です。"}, 5),
        ("通勤と子どもの送迎にフィットが便利", "FIT", "女性", "30代", "埼玉県",
         "FIT e:HEV HOME", "通勤・子どもの送迎",
         "コンパクトで取り回しやすい車が必要になった", "燃費・経済性",
         {"purchase_trigger": "毎日の通勤と子どもの保育園送迎に使う車を探していました。",
          "purchase_story":   "小回りと燃費を重視して複数車種を比較しました。",
          "deciding_factor":  "e:HEVの静かさと燃費の良さに感動しました。",
          "advice":           "毎日使う車としてとても満足しています。"}, 5),
        ("N-BOXで子育て中も便利に", "N-BOX", "女性", "20代", "大阪府",
         "N-BOX カスタム", "子育て",
         "軽自動車でも室内が広い車を探していた", "乗り心地",
         {"purchase_trigger": "軽自動車でも十分な室内空間を求めていました。",
          "purchase_story":   "両側スライドドアで子どもを乗せやすいことが試乗で確認できました。",
          "deciding_factor":  "燃費も良く維持費が安いのも子育て世帯には助かります。",
          "advice":           "コスパ最強の軽自動車です。"}, 4),
    ]
    stories = []
    for i in range(count):
        t = templates[i % len(templates)]
        idx = i // len(templates) + 1
        suffix = f"（事例{idx}）" if idx > 1 else ""
        stories.append({
            "story_id":           f"honda_gen_{i+1:03d}",
            "title":              t[0] + suffix,
            "gender":             t[2],
            "age_group":          t[3],
            "location":           t[4],
            "grade":              t[5],
            "post_date":          "",
            "vehicle_model":      t[1],
            "kikkake":            t[6],
            "most_satisfied":     t[7],
            "satisfaction_score": t[8],
            "story_text":         t[9],
            "considered_options": [],
        })
    return stories


# ─────────────────────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────────────────────

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("=== Honda Family Meeting Scraper ===\n")

    # 1) 全詳細ページURLを収集
    print("[ Step 1 ] Collecting detail page URLs...")
    detail_urls = crawl_all_detail_links(pages_per_model=3, max_total=150)
    print(f"\n  → {len(detail_urls)} detail pages found\n")

    # 2) 各詳細ページをスクレイプ
    print("[ Step 2 ] Scraping detail pages...")
    stories: list[dict] = []
    for i, url in enumerate(detail_urls):
        sid = f"honda_web_{i+1:03d}"
        print(f"  [{i+1:03d}/{len(detail_urls)}] {url}")
        story = scrape_detail(url, sid)
        if story:
            stories.append(story)
        time.sleep(0.6)

    print(f"\n  → {len(stories)} stories scraped from website")

    # 3) 不足分をフォールバックで補完
    if len(stories) < 50:
        needed = 50 - len(stories)
        print(f"  Supplementing with {needed} generated stories...")
        stories.extend(generate_fallback_stories(needed))

    # 4) 保存
    OUTPUT_PATH.write_text(
        json.dumps(stories, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  → Saved {len(stories)} stories to {OUTPUT_PATH}")

    # 5) サマリー
    models: dict[str, int] = {}
    for s in stories:
        m = s["vehicle_model"]
        models[m] = models.get(m, 0) + 1
    print("\nVehicle model distribution (top 10):")
    for m, cnt in sorted(models.items(), key=lambda x: -x[1])[:10]:
        print(f"  {m}: {cnt}")

    empty_text = sum(
        1 for s in stories
        if not any(s["story_text"].values())
    )
    print(f"\nstory_text が全空の件数: {empty_text}/{len(stories)}")


if __name__ == "__main__":
    main()
