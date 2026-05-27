"""
Phase 7: Streamlit Sales UI — Lexus Intelligence Clean Design
"""
import os
import uuid
from datetime import datetime as _dt
import requests
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

_NEEDS_LABEL = {
    "safety":          "安全性",
    "space":           "広さ・収納",
    "fuel_efficiency": "燃費",
    "comfort":         "快適性",
    "design":          "デザイン",
    "technology":      "先進技術",
    "family":          "ファミリー",
    "offroad":         "悪路走破",
}

st.set_page_config(
    page_title="LEXUS INTELLIGENCE",
    page_icon="L",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Clean CSS (white / consumer-friendly) ─────────────────────────────────
CLEAN_CSS = """
<style>
:root {
    --bg:        #F5F7FA;
    --bg-card:   #FFFFFF;
    --bg-hover:  #EEF2F7;
    --navy:      #1A365D;
    --navy-lt:   #2D5A8E;
    --gold:      #B8920C;
    --text:      #0D1B2A;
    --text-2:    #4A5568;
    --text-3:    #94A3B8;
    --border:    #E2E8F0;
    --border-2:  #CBD5E1;
    --green:     #16A34A;
    --orange:    #D97706;
    --red:       #DC2626;
    --shadow:    0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 8px rgba(0,0,0,0.08);
    --radius:    6px;
}

/* ─── App background ─────────────────────────────────────────────────── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stMain"],
.main,
.block-container {
    background-color: var(--bg) !important;
}
#MainMenu, footer, header { visibility: hidden; }

/* ─── Scrollbar ──────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-3); }

/* ─── Typography ─────────────────────────────────────────────────────── */
* { box-sizing: border-box; }
body { color: var(--text); }
h1,h2,h3,h4,h5,h6 { color: var(--text) !important; font-weight: 600 !important; }
p, li, span, div { color: var(--text); }
label, .stMarkdown p { color: var(--text) !important; }
small, .stCaption p, [data-testid="caption"] { color: var(--text-2) !important; }

/* ─── Masthead ───────────────────────────────────────────────────────── */
.lexus-masthead {
    padding: 22px 0 14px;
    margin-bottom: 8px;
    border-bottom: 2px solid var(--navy);
    text-align: center;
    background: var(--bg);
}
.lexus-wordmark {
    font-size: 15px;
    letter-spacing: 7px;
    color: var(--navy);
    font-weight: 700;
    text-transform: uppercase;
    margin: 0;
}
.lexus-tagline {
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--text-2);
    text-transform: uppercase;
    margin-top: 5px;
}

/* ─── Tabs ───────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background-color: var(--bg-card) !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
    padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--text-2) !important;
    font-size: 11px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    padding: 12px 22px !important;
    background-color: transparent !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    font-weight: 500 !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: var(--navy) !important;
    border-bottom-color: var(--navy) !important;
    background-color: transparent !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--navy) !important;
    height: 2px !important;
}
.stTabs [data-baseweb="tab-border"] { background-color: var(--border) !important; }
.stTabs [data-baseweb="tab-panel"] {
    background-color: var(--bg) !important;
    padding-top: 24px !important;
}

/* ─── Inputs ─────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-size: 14px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--navy) !important;
    box-shadow: 0 0 0 2px rgba(26,54,93,0.12) !important;
}
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stMultiSelect label, .stSlider label {
    color: var(--text-2) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
}
div[data-baseweb="select"] > div {
    background-color: var(--bg-card) !important;
    border-color: var(--border-2) !important;
    color: var(--text) !important;
    border-radius: var(--radius) !important;
}
div[data-baseweb="select"] span { color: var(--text) !important; }
[data-baseweb="menu"],
[data-baseweb="menu"] > ul,
[data-baseweb="menu"] li,
[data-baseweb="menu"] li > div,
[data-baseweb="menu"] li span,
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="option"],
[data-baseweb="popover"] [role="option"] span,
[data-baseweb="popover"] [role="option"] div {
    background-color: var(--bg-card) !important;
    color: var(--text) !important;
}
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] li[aria-selected="true"],
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [role="option"][aria-selected="true"] {
    background-color: var(--bg-hover) !important;
    color: var(--text) !important;
}
[data-baseweb="popover"] > div {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow-md) !important;
    border-radius: var(--radius) !important;
}
span[data-baseweb="tag"] {
    background-color: var(--navy) !important;
    border: 1px solid var(--navy) !important;
    border-radius: 4px !important;
}
span[data-baseweb="tag"] span { color: #FFFFFF !important; font-size: 12px !important; }

/* ─── Buttons ────────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: var(--radius) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="primary"],
.stButton > button[kind="primary"] * {
    color: #FFFFFF !important;
}
.stButton > button[kind="primary"] {
    background-color: var(--navy) !important;
    border: none !important;
    padding: 10px 24px !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: var(--navy-lt) !important;
    box-shadow: var(--shadow-md) !important;
}
.stButton > button[kind="secondary"],
.stButton > button:not([kind]) {
    background-color: var(--bg-card) !important;
    color: var(--navy) !important;
    border: 1px solid var(--navy) !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind]):hover { background-color: var(--bg-hover) !important; }
.stFormSubmitButton > button,
[data-testid="stFormSubmitButton"] button,
.stFormSubmitButton > button *,
[data-testid="stFormSubmitButton"] button * {
    color: #FFFFFF !important;
}
.stFormSubmitButton > button,
[data-testid="stFormSubmitButton"] button {
    background-color: var(--navy) !important;
    border: none !important;
    font-size: 13px !important;
    border-radius: var(--radius) !important;
    padding: 10px 24px !important;
}
.stFormSubmitButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover { background-color: var(--navy-lt) !important; }

/* ─── Containers / Cards ─────────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
}

/* ─── Progress bar ───────────────────────────────────────────────────── */
[data-testid="stProgressBar"] > div {
    background-color: var(--border) !important;
    border-radius: 2px !important;
    height: 4px !important;
}
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, var(--navy), var(--navy-lt)) !important;
    border-radius: 2px !important;
}

/* ─── Metrics ────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 16px !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="stMetricValue"] { color: var(--navy) !important; font-weight: 600 !important; }
[data-testid="stMetricLabel"] { color: var(--text-2) !important; font-size: 12px !important; }

/* ─── Alerts ─────────────────────────────────────────────────────────── */
[data-testid="stAlert"],
.stInfo > div, .stSuccess > div, .stWarning > div, .stError > div {
    background-color: var(--bg-card) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
}
.stInfo > div    { border-left-color: var(--navy) !important; }
.stSuccess > div { border-left-color: var(--green) !important; }
.stWarning > div { border-left-color: var(--orange) !important; }
.stError > div   { border-left-color: var(--red) !important; }

/* ─── Dataframe ──────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] iframe, .dvn-scroll-inner, .glideDataEditor {
    background-color: var(--bg-card) !important;
    color: var(--text) !important;
}

/* ─── Expander ───────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background-color: var(--bg-card) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}
.streamlit-expanderContent {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 var(--radius) var(--radius) !important;
}

/* ─── Divider ────────────────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 20px 0 !important; }

/* ─── Slider ─────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background-color: var(--navy) !important;
    border-color: var(--navy) !important;
}

/* ─── Section label ──────────────────────────────────────────────────── */
.section-label {
    font-size: 11px;
    letter-spacing: 2px;
    color: var(--text-2);
    text-transform: uppercase;
    font-weight: 600;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

/* ─── Recommendation card ────────────────────────────────────────────── */
.reco-header {
    display: flex;
    align-items: baseline;
    gap: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 10px;
}
.reco-rank { font-size: 11px; letter-spacing: 2px; color: var(--text-3); text-transform: uppercase; min-width: 30px; }
.reco-model { font-size: 22px; font-weight: 700; letter-spacing: 4px; color: var(--navy); text-transform: uppercase; }
.reco-grade {
    font-size: 11px; letter-spacing: 1px; color: var(--navy);
    border: 1px solid var(--navy); padding: 3px 10px;
    border-radius: 3px; text-transform: uppercase; font-weight: 500;
}
.reco-price { margin-left: auto; font-size: 12px; color: var(--text-2); text-align: right; }
.reco-score-row { display: flex; align-items: center; gap: 12px; margin: 6px 0 10px 0; }
.reco-score-val { font-size: 28px; font-weight: 300; color: var(--navy); line-height: 1; }
.reco-score-unit { font-size: 10px; letter-spacing: 2px; color: var(--text-3); text-transform: uppercase; align-self: flex-end; padding-bottom: 2px; }
.reco-reason { font-size: 12px; color: var(--text-2); margin-left: auto; text-align: right; max-width: 60%; }

/* ─── Appeal points ──────────────────────────────────────────────────── */
.appeal-wrap {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-top: 3px solid var(--navy);
    border-radius: 0 0 var(--radius) var(--radius);
    padding: 16px 20px;
    margin-top: 12px;
}
.appeal-title { font-size: 10px; letter-spacing: 2px; color: var(--navy); text-transform: uppercase; font-weight: 600; margin: 0 0 12px 0; }
.appeal-list  { list-style: none; padding: 0; margin: 0; }
.appeal-item  { display: flex; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--border); line-height: 1.5; align-items: flex-start; }
.appeal-item:last-child { border-bottom: none; }
.appeal-bullet { color: var(--navy); flex-shrink: 0; font-size: 12px; font-weight: 700; min-width: 22px; text-align: right; padding-top: 2px; }
.appeal-content { flex: 1; min-width: 0; }
.appeal-text { font-size: 13px; color: var(--text); margin-bottom: 5px; }
.appeal-tags { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.need-tag {
    display: inline-block;
    background: rgba(26,54,93,0.08);
    border: 1px solid var(--navy);
    color: var(--navy);
    font-size: 10px; font-weight: 600;
    padding: 1px 7px; border-radius: 3px;
}
.kw-tag      { font-size: 11px; color: var(--text-2); }
.no-match-tag{ font-size: 10px; color: var(--text-3); font-style: italic; }

/* ─── Talk examples ──────────────────────────────────────────────────── */
.talk-wrap  { margin-top: 16px; }
.talk-title { font-size: 10px; letter-spacing: 2px; color: var(--text-2); text-transform: uppercase; font-weight: 600; margin: 0 0 10px 0; }
.talk-card  {
    background: var(--bg-card); border: 1px solid var(--border);
    border-left: 3px solid var(--navy);
    border-radius: 0 var(--radius) var(--radius) 0;
    padding: 14px 18px; margin-bottom: 8px;
    box-shadow: var(--shadow);
}
.talk-num  { font-size: 10px; letter-spacing: 2px; color: var(--navy); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 6px; }
.talk-text { font-size: 13px; line-height: 1.75; color: var(--text); margin: 0; }

/* ─── Explorer (Knowledge Graph) ────────────────────────────────────── */
.explorer-node-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 12px 14px;
    box-shadow: var(--shadow);
}
.explorer-type-label {
    font-size: 10px; letter-spacing: 2px; color: var(--navy);
    text-transform: uppercase; font-weight: 600;
    margin-bottom: 8px; padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}
.explorer-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 0; border-bottom: 1px solid var(--border);
    font-size: 13px;
}
.explorer-row:last-child { border-bottom: none; }
.explorer-name  { color: var(--text); flex: 1; }
.explorer-score {
    color: var(--navy); font-weight: 600; font-size: 12px;
    background: rgba(26,54,93,0.08); padding: 1px 8px; border-radius: 3px;
    margin-left: 8px; white-space: nowrap;
}

/* ─── Verification ───────────────────────────────────────────────────── */
.verify-field-header {
    font-size: 12px; font-weight: 600; color: var(--navy);
    margin: 4px 0 2px; letter-spacing: 0.3px;
}
.verify-extracted {
    font-size: 13px; background: rgba(26,54,93,0.06);
    border: 1px solid var(--border); border-radius: 4px;
    padding: 5px 10px; color: var(--text); margin-bottom: 6px;
    display: inline-block;
}

/* ─── Explorer two-pane (Consumer Area / Product Area) ───────────── */
span.area-badge-consumer {
    display: inline-block; background: var(--navy) !important;
    color: #FFFFFF !important;
    font-size: 10px; letter-spacing: 2.5px; font-weight: 700;
    text-transform: uppercase; padding: 5px 16px; border-radius: 3px;
}
span.area-badge-product {
    display: inline-block; background: var(--gold) !important;
    color: #FFFFFF !important;
    font-size: 10px; letter-spacing: 2.5px; font-weight: 700;
    text-transform: uppercase; padding: 5px 16px; border-radius: 3px;
}
.explorer-bridge-wrap {
    display: flex; flex-direction: column; align-items: center;
    padding: 24px 0; gap: 6px;
}
.bridge-vert-line {
    width: 2px; min-height: 28px; flex: 1;
    background: linear-gradient(to bottom, transparent, var(--border-2), transparent);
}
.bridge-count-badge {
    background: var(--navy) !important; color: #FFFFFF !important;
    font-size: 15px; font-weight: 700;
    padding: 7px 12px; border-radius: 22px; text-align: center;
    min-width: 46px; box-shadow: 0 2px 8px rgba(26,54,93,0.28);
}
.bridge-label {
    font-size: 9px !important; color: var(--text-3) !important;
    letter-spacing: 1.5px; text-transform: uppercase; text-align: center;
}
.bridge-arrow-icon {
    font-size: 22px; color: var(--navy) !important; font-weight: 900; line-height: 1;
}
.grade-badge {
    display: inline-block;
    background: rgba(184,146,12,0.12); border: 1px solid var(--gold);
    color: var(--gold) !important; font-size: 10px; font-weight: 600;
    padding: 2px 8px; border-radius: 3px; margin: 2px;
}
.grade-badge-sm {
    display: inline-block;
    background: rgba(184,146,12,0.10); border: 1px solid var(--gold);
    color: #96760A !important; font-size: 9px; font-weight: 600;
    padding: 1px 5px; border-radius: 2px;
}
.explorer-row-vehicle {
    padding: 6px 0; border-bottom: 1px solid var(--border);
}
.explorer-row-vehicle:last-child { border-bottom: none; }
</style>
"""

st.markdown(CLEAN_CSS, unsafe_allow_html=True)

# ── Masthead ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="lexus-masthead">
  <p class="lexus-wordmark">Knowledge Mixer Origin PoC</p>
  <p class="lexus-tagline">AI-Powered Recommendation System &nbsp;&middot;&nbsp; Neo4j Knowledge Graph + Claude AI</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────
for _k, _v in {
    "recommendations": [],
    "last_request": {},
    "explain_results": {},
    "talk_results": {},
    "consumer_id": "sale_" + str(uuid.uuid4())[:8],
    "similar_consumers": None,
    # KG Explorer
    "kg_filter_values": {},
    "kg_explorer_results": None,
    # KG Verification
    "verify_stories": [],
    "verify_selected": None,
    "verify_comparison": None,
    "verify_stats": None,
    "verify_improvements": None,
    # Graph
    "graph_stats": None,
    "graph_vehicles": None,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Dynamic KG filter callback ─────────────────────────────────────────────
def _update_kg_filters():
    """フィルター変更時に動的エンドポイントを呼び出し、有効な選択肢だけに絞り込む。"""
    payload = {
        "gender":              st.session_state.get("kg_gender", []),
        "age_group":           st.session_state.get("kg_age", []),
        "location":            st.session_state.get("kg_loc", []),
        "country":             st.session_state.get("kg_country", []),
        "occupation":          st.session_state.get("kg_occ", []),
        "income_range":        st.session_state.get("kg_inc", []),
        "driving_frequency":   st.session_state.get("kg_drv", []),
        "mobility_pattern":    st.session_state.get("kg_mob", []),
        "trigger":             st.session_state.get("kg_trigger", []),
        "sub_trigger":         st.session_state.get("kg_sub_trigger", []),
        "need":                st.session_state.get("kg_need", []),
        "sub_need":            st.session_state.get("kg_sub_need", []),
        "evaluation_criteria": st.session_state.get("kg_ec", []),
        "purchase_driver":     st.session_state.get("kg_pd", []),
        "vehicle_model":       st.session_state.get("kg_vm", []),
        "feature":             st.session_state.get("kg_feature", []),
    }
    try:
        r = requests.post(f"{API_BASE}/graph/filter-values/dynamic", json=payload, timeout=15)
        if r.ok:
            st.session_state.kg_filter_values = r.json()
    except Exception:
        pass


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "顧客情報 · 推薦",
    "類似顧客事例",
    "販売記録 · カタログ",
    "Knowledge Graph",
    "KGデータ検証",
])


# ═══════════════════════════════════════════════════════════════════════════
# Tab 1: 顧客情報入力 + 推薦
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<p class="section-label">顧客情報入力</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        family_size = st.number_input("家族人数", min_value=1, max_value=10, value=4, step=1)
        usage = st.selectbox(
            "主な使用用途",
            ["family_use", "commute", "business", "outdoor", "leisure"],
            format_func=lambda x: {
                "family_use": "ファミリー用", "commute": "通勤・通学",
                "business": "ビジネス", "outdoor": "アウトドア", "leisure": "レジャー",
            }.get(x, x),
        )
        budget = st.number_input("予算（万円）", min_value=100, max_value=3000, value=1000, step=50)
        budget_yen = budget * 10_000

    with col2:
        needs_options = {
            "safety":          "安全性",
            "space":           "広さ・収納",
            "fuel_efficiency": "燃費・経済性",
            "comfort":         "乗り心地",
            "design":          "デザイン",
            "technology":      "先進技術",
            "family":          "ファミリー向け機能",
            "offroad":         "悪路走破性",
        }
        selected_needs = st.multiselect(
            "重視するポイント",
            options=list(needs_options.keys()),
            default=["safety", "space"],
            format_func=lambda x: needs_options.get(x, x),
        )
        free_text = st.text_area(
            "担当者メモ（自由記述）",
            placeholder="例: 2列目に大きなチャイルドシートを積む予定。週末は山道も走る。",
            height=115,
        )

    st.write("")
    if st.button("推薦を取得", type="primary", use_container_width=True):
        if not selected_needs:
            st.warning("重視するポイントを1つ以上選択してください。")
        else:
            with st.spinner("推薦を計算中..."):
                payload = {
                    "family_size": family_size,
                    "needs": selected_needs,
                    "budget": budget_yen,
                    "usage": usage,
                    "free_text": free_text,
                }
                try:
                    resp = requests.post(f"{API_BASE}/recommend", json=payload, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                    st.session_state.recommendations = data.get("recommendations", [])
                    st.session_state.last_request = payload
                    st.session_state.explain_results = {}
                    st.session_state.talk_results = {}
                    st.success(f"{len(st.session_state.recommendations)} 件の推薦が見つかりました")
                except requests.exceptions.ConnectionError:
                    st.error("APIサーバーに接続できません。`uvicorn api.api_server:app` を起動してください。")
                except Exception as e:
                    st.error(f"エラー: {e}")

    if st.session_state.recommendations:
        st.write("")
        st.markdown('<p class="section-label">推薦結果</p>', unsafe_allow_html=True)
        req = st.session_state.last_request

        for i, rec in enumerate(st.session_state.recommendations):
            model       = rec["model"]
            score_pct   = int(rec["score"] * 100)
            quick_grade = rec.get("quick_grade") or "標準グレード"
            price_range = rec.get("price_range") or ""
            appeal_points = rec.get("appeal_points", [])
            talk_result   = st.session_state.talk_results.get(model)

            with st.container(border=True):
                price_display = f"<span>{price_range}</span>" if price_range else ""
                st.markdown(f"""
<div class="reco-header">
  <span class="reco-rank">No.{i+1}</span>
  <span class="reco-model">{model}</span>
  <span class="reco-grade">{quick_grade}</span>
  <span class="reco-price">{price_display}</span>
</div>
<div class="reco-score-row">
  <span class="reco-score-val">{score_pct}</span>
  <span class="reco-score-unit">適合度 %</span>
  <span class="reco-reason">{rec.get("reason", "")}</span>
</div>
""", unsafe_allow_html=True)
                st.progress(rec["score"])

                if appeal_points:
                    items_html = ""
                    for j, p in enumerate(appeal_points, 1):
                        text    = p["text"] if isinstance(p, dict) else p
                        m_needs = p.get("matched_needs", []) if isinstance(p, dict) else []
                        m_kws   = p.get("matched_keywords", []) if isinstance(p, dict) else []

                        if m_needs:
                            need_badges = "".join(
                                f'<span class="need-tag">{_NEEDS_LABEL.get(n, n)}</span>'
                                for n in m_needs
                            )
                            kw_str   = "　".join(f"「{k}」" for k in m_kws)
                            tags_html = (
                                f'<div class="appeal-tags">{need_badges}'
                                f'<span class="kw-tag">{kw_str}</span></div>'
                            )
                        else:
                            tags_html = '<div class="appeal-tags"><span class="no-match-tag">参考情報</span></div>'

                        items_html += (
                            f'<li class="appeal-item">'
                            f'<span class="appeal-bullet">{j}</span>'
                            f'<div class="appeal-content">'
                            f'<div class="appeal-text">{text}</div>'
                            f'{tags_html}</div></li>'
                        )

                    st.markdown(f"""
<div class="appeal-wrap">
  <p class="appeal-title">訴求ポイント — カタログ実データ Top {len(appeal_points)}</p>
  <ul class="appeal-list">{items_html}</ul>
</div>
""", unsafe_allow_html=True)

                    st.write("")
                    point_texts = [(p["text"] if isinstance(p, dict) else p) for p in appeal_points]
                    sel_key = f"sel_{model}"
                    selected = st.multiselect(
                        "トーク例に使う訴求ポイントを選択",
                        options=point_texts, default=point_texts[:3],
                        key=sel_key,
                        help="選択したポイントを元にAIが営業トークを3パターン生成します",
                    )
                    btn_label = "トーク例を再生成" if talk_result else "トーク例を生成"
                    if st.button(btn_label, key=f"gen_talk_{model}", type="primary"):
                        if not selected:
                            st.warning("訴求ポイントを1つ以上選択してください。")
                        else:
                            with st.spinner(f"{model} の営業トークを生成中..."):
                                ex_payload = {
                                    "model_name":     model,
                                    "family_size":    req.get("family_size", 4),
                                    "needs":          req.get("needs", []),
                                    "budget":         req.get("budget", 0),
                                    "usage":          req.get("usage", ""),
                                    "free_text":      req.get("free_text", ""),
                                    "selected_points": selected,
                                }
                                try:
                                    ex_resp = requests.post(f"{API_BASE}/explain", json=ex_payload, timeout=30)
                                    ex_resp.raise_for_status()
                                    data = ex_resp.json()
                                    st.session_state.talk_results[model] = data.get("talk_examples", [])
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"生成エラー: {e}")

                if talk_result:
                    talk_cards_html = "".join(
                        f'<div class="talk-card">'
                        f'<span class="talk-num">トーク例 {j}</span>'
                        f'<p class="talk-text">{t}</p></div>'
                        for j, t in enumerate(talk_result, 1)
                    )
                    st.markdown(f"""
<div class="talk-wrap">
  <p class="talk-title">営業トーク例</p>
  {talk_cards_html}
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Tab 2: 類似顧客事例
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<p class="section-label">類似顧客事例</p>', unsafe_allow_html=True)
    st.caption("同じニーズを持つ過去の購買顧客のストーリーを参照します。データが蓄積されるほど精度が高まります。")

    if not st.session_state.last_request:
        st.info("「顧客情報 · 推薦」タブで推薦を取得すると、類似事例が表示されます。")
    else:
        req = st.session_state.last_request
        st.caption(
            f"検索条件: {req.get('family_size')}人家族 / "
            f"ニーズ: {', '.join(req.get('needs', []))}"
        )
        if st.button("類似顧客を検索", type="secondary"):
            with st.spinner("類似顧客を検索中..."):
                try:
                    sim_resp = requests.post(
                        f"{API_BASE}/similar_stories",
                        json={"needs": req.get("needs", []),
                              "family_size": req.get("family_size", 4), "limit": 6},
                        timeout=15,
                    )
                    sim_resp.raise_for_status()
                    st.session_state.similar_consumers = sim_resp.json().get("consumers", [])
                except Exception as e:
                    st.error(f"検索エラー: {e}")

        consumers = st.session_state.get("similar_consumers")
        if consumers:
            st.write(f"**{len(consumers)}件** の類似事例が見つかりました")
            for c in consumers:
                matched = c.get("matched", 0)
                profile = " / ".join(filter(None, [c.get("gender"), c.get("age_group")]))
                with st.expander(
                    f"[ニーズ一致 {matched}件]  {c.get('title', c['consumer_id'])} "
                    f"({profile or '不明'}) → {c['selected_vehicle']} を購入",
                    expanded=False,
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**家族人数:** {c.get('family_size') or '不明'}人")
                        st.write(f"**用途:** {c.get('usage') or '不明'}")
                        st.write(f"**購入きっかけ:** {c.get('kikkake') or '不明'}")
                    with col_b:
                        st.write(f"**最も満足した点:** {c.get('most_satisfied') or '不明'}")
                        score = c.get("satisfaction_score")
                        if score:
                            st.write(f"**満足度:** {'★' * int(score)}{'☆' * (5 - int(score))}")
                    if c.get("deciding_factor"):
                        st.write(f"**決め手:** {c['deciding_factor']}")
                    if c.get("purchase_trigger"):
                        st.caption(f"購入の経緯: {c['purchase_trigger'][:200]}")
        elif consumers is not None:
            st.info("類似事例が見つかりませんでした。データが増えると精度が上がります。")


# ═══════════════════════════════════════════════════════════════════════════
# Tab 3: 販売記録 & カタログ管理
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<p class="section-label">販売記録入力</p>', unsafe_allow_html=True)
    st.caption("実際の販売情報をグラフに反映します。")

    col_id, col_new = st.columns([4, 1])
    with col_id:
        st.info(f"顧客ID（自動採番）: **{st.session_state.consumer_id}**")
    with col_new:
        st.write("")
        if st.button("IDを再発行"):
            st.session_state.consumer_id = "sale_" + str(uuid.uuid4())[:8]
            st.rerun()

    with st.form("sales_form"):
        st.subheader("顧客プロフィール")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            gender = st.selectbox("性別", ["", "男性", "女性", "その他"])
        with col_p2:
            age_group = st.selectbox("年代", ["", "10代", "20代", "30代", "40代", "50代", "60代", "70代以上"])
        with col_p3:
            location = st.text_input("都道府県", placeholder="東京都")
        with col_p4:
            country = st.text_input("国", value="日本", placeholder="日本")

        st.subheader("購入車種")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            vehicle_model = st.text_input("購入車種 *", placeholder="例: NX, RX, LX")
            grade = st.text_input("グレード", placeholder="例: version L AWD")
        with col_v2:
            kikkake_options = [
                "", "新型車が気に入ったから", "今の車が古くなったから",
                "家族が増えたから", "ライフスタイルが変わったから",
                "燃費が気になったから", "安全性能を重視したから",
                "デザインが気に入ったから", "その他",
            ]
            kikkake = st.selectbox("購入のきっかけ", kikkake_options)
            most_satisfied = st.text_input("最も満足した点", placeholder="例: 安全性能, 乗り心地")

        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            title = st.text_input("タイトル（任意）", placeholder="例: 家族4人でレクサス初体験！")
        with col_s2:
            satisfaction_score = st.slider("満足度", min_value=1, max_value=5, value=5, format="%d 点")

        st.subheader("顧客プロフィール（詳細）")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            occupation    = st.text_input("職業", placeholder="例: 会社員・医師・教員")
            income_range  = st.selectbox("年収帯", ["", "〜300万円", "300〜500万円", "500〜700万円", "700〜1000万円", "1000万円〜"])
        with col_d2:
            driving_frequency = st.selectbox("運転頻度", ["", "毎日", "週数回", "週末のみ", "月数回"])
            mobility_pattern  = st.selectbox("主な移動パターン", ["", "通勤・通学", "レジャー", "長距離ドライブ", "市街地", "複合"])

        col_v1b, col_v2b = st.columns(2)
        with col_v1b:
            values_input   = st.text_input("価値観・重視すること", placeholder="例: 家族の安全重視・環境意識高い")
        with col_v2b:
            physical_notes = st.text_input("身体特性・特記事項（任意）", placeholder="例: 高齢・車いす使用・背が高い")

        purchase_driver_input = st.text_input(
            "購入の決め手", placeholder="例: 安全性能が決め手。試乗した際の静粛性に感動した。")
        considered_options_text = st.text_input(
            "検討した他の車種（カンマ区切り）", placeholder="例: RX, NX, ランドクルーザー")

        st.subheader("購買ストーリー")
        purchase_trigger = st.text_area("購入のきっかけ（詳細）", height=80,
            placeholder="どんな出来事や気持ちの変化がきっかけでしたか？")
        purchase_story = st.text_area("ご購入までのエピソード・ストーリー", height=100,
            placeholder="実際に購入するまでの経緯を教えてください。")
        deciding_factor = st.text_area("決め手", height=80,
            placeholder="最終的にこの車種を選んだ理由は何ですか？")
        advice = st.text_area("同じクルマを検討している人へのアドバイス", height=80,
            placeholder="同じような方へひとこと。")

        submitted = st.form_submit_button("販売記録を保存", type="primary")
        if submitted:
            if not vehicle_model:
                st.error("購入車種は必須です。")
            else:
                considered = [v.strip() for v in considered_options_text.split(",") if v.strip()]
                payload = {
                    "consumer_id":     st.session_state.consumer_id,
                    "title":           title or f"{vehicle_model}購入",
                    "gender":          gender,
                    "age_group":       age_group,
                    "location":        location,
                    "country":         country,
                    "vehicle_model":   vehicle_model,
                    "grade":           grade,
                    "kikkake":         kikkake,
                    "most_satisfied":  most_satisfied,
                    "satisfaction_score": satisfaction_score,
                    "story_text": {
                        "purchase_trigger": purchase_trigger,
                        "purchase_story":   purchase_story,
                        "deciding_factor":  deciding_factor,
                        "advice":           advice,
                    },
                    "considered_options":   considered,
                    "occupation":           occupation,
                    "income_range":         income_range,
                    "driving_frequency":    driving_frequency,
                    "mobility_pattern":     mobility_pattern,
                    "values":               values_input,
                    "physical_notes":       physical_notes,
                    "purchase_driver":      purchase_driver_input,
                }
                try:
                    resp = requests.post(f"{API_BASE}/sales_feedback", json=payload, timeout=15)
                    resp.raise_for_status()
                    result = resp.json()
                    st.success(
                        f"記録完了！  顧客ID: {result['consumer_id']} / "
                        f"{vehicle_model} の重みを {result['weight_delta']:+.3f} 更新しました"
                    )
                    st.session_state.consumer_id = "sale_" + str(uuid.uuid4())[:8]
                    st.rerun()
                except requests.exceptions.ConnectionError:
                    st.error("APIサーバーに接続できません。")
                except Exception as e:
                    st.error(f"エラー: {e}")

    st.divider()
    st.markdown('<p class="section-label">カタログ管理</p>', unsafe_allow_html=True)

    scan_tab_pdf, scan_tab_vehicle, scan_tab_maker, scan_tab_list = st.tabs([
        "📄 PDFスキャン",
        "🌐 車種TOPスキャン",
        "🏭 メーカーTOPスキャン",
        "📋 URLリスト一括スキャン",
    ])

    # ── PDFスキャン ──────────────────────────────────────────────────────────
    with scan_tab_pdf:
        st.caption("PDFカタログをフォルダに追加してから「スキャン実行」を押すと、グラフが自動更新されます。")
        st.code("data/raw/lexus_catalogs/<車種名>/", language=None)
        if st.button("カタログをスキャンしてグラフを更新", type="primary", key="scan_pdf_btn"):
            with st.spinner("PDFを読み込み中... (1〜2分かかります)"):
                try:
                    resp = requests.post(f"{API_BASE}/rescan_catalog", timeout=300)
                    resp.raise_for_status()
                    result = resp.json()
                    if result["status"] == "ok":
                        st.success(f"完了: {result['model_count']} 車種を更新しました")
                    else:
                        st.warning(f"一部エラー: {result}")
                except requests.exceptions.ConnectionError:
                    st.error("APIサーバーに接続できません。")
                except Exception as e:
                    st.error(f"エラー: {e}")

        st.divider()
        st.markdown("**🔄 グラフ手動反映**")
        st.caption(
            "Webスキャン済みの製品データが推薦や KG に反映されていない場合、"
            "ここをクリックして product_features.json を Neo4j に書き込みます。"
        )
        if st.button("スキャン済みデータをグラフに反映", key="apply_graph_btn"):
            with st.spinner("Neo4j に書き込み中..."):
                try:
                    resp = requests.post(f"{API_BASE}/rescan_web/apply-graph", timeout=120)
                    if resp.ok:
                        r = resp.json()
                        if r["status"] == "ok":
                            st.success(
                                f"✅ グラフ反映完了！ 登録済み: {r.get('total_model_count','?')} 車種"
                            )
                        else:
                            st.error(f"反映エラー: {r.get('graph','')}")
                    else:
                        st.error(resp.json().get("detail", resp.text))
                except requests.exceptions.ConnectionError:
                    st.error("APIサーバーに接続できません。")
                except Exception as e:
                    st.error(f"エラー: {e}")

    # ── 車種TOPスキャン ──────────────────────────────────────────────────────
    with scan_tab_vehicle:
        st.caption(
            "車種トップページのURLを入力すると、配下のサブページ（グレード一覧・デザイン・性能・装備など）を"
            "自動的に収集して車種情報をグラフに登録します。"
        )
        with st.expander("URLの例（Honda INSIGHT）", expanded=False):
            st.markdown("""
**車種TOP URL**
```
https://www.honda.co.jp/INSIGHT/
```
**自動収集されるサブページ（例）**
```
https://www.honda.co.jp/INSIGHT/webcatalog/type/list/
https://www.honda.co.jp/INSIGHT/webcatalog/design/
https://www.honda.co.jp/INSIGHT/webcatalog/performance/
https://www.honda.co.jp/INSIGHT/webcatalog/utility/
https://www.honda.co.jp/INSIGHT/essentials/
```
""")

        wv_col1, wv_col2 = st.columns([2, 3])
        with wv_col1:
            wv_model = st.text_input(
                "車種名（半角英大文字推奨）",
                placeholder="例: INSIGHT",
                key="web_vehicle_model",
            )
        with wv_col2:
            wv_url = st.text_input(
                "車種TOP URL",
                placeholder="例: https://www.honda.co.jp/INSIGHT/",
                key="web_vehicle_url",
            )

        wv_graph = st.checkbox("スキャン後にグラフも更新する", value=True, key="web_vehicle_graph")

        if st.button("車種ページをスキャン", type="primary", key="web_vehicle_btn",
                     disabled=not (wv_model.strip() and wv_url.strip())):
            with st.spinner(f"{wv_model} をスキャン中... （ページ収集 + AI解析：30秒〜2分）"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/rescan_web/vehicle",
                        json={
                            "model_name": wv_model.strip(),
                            "url": wv_url.strip(),
                            "update_graph": wv_graph,
                        },
                        timeout=300,
                    )
                    if resp.ok:
                        r = resp.json()
                        st.success(
                            f"✅ **{r['model_name']}** のスキャン完了！  "
                            f"カテゴリ: {r.get('category','—')} ／ "
                            f"グレード: {len(r.get('grades', []))} 種  "
                            f"（登録済み: {r.get('total_model_count', '?')} 車種）"
                        )
                        if r.get("grades"):
                            st.markdown(
                                " ".join(
                                    f'<span style="background:rgba(184,146,12,.12);border:1px solid #B8920C;'
                                    f'color:#7A5F00;font-size:11px;padding:2px 8px;border-radius:3px;'
                                    f'margin:2px;display:inline-block;">{g}</span>'
                                    for g in r["grades"]
                                ),
                                unsafe_allow_html=True,
                            )
                        if r.get("graph_steps"):
                            gsteps = r["graph_steps"]
                            if all(v == "ok" for v in gsteps.values()):
                                st.caption("グラフ更新: ✓ 完了")
                            else:
                                st.caption(f"グラフ更新（一部エラー）: {gsteps}")
                    else:
                        detail = resp.json().get("detail", resp.text)
                        st.error(f"スキャンエラー: {detail}")
                except requests.exceptions.ConnectionError:
                    st.error("APIサーバーに接続できません。")
                except Exception as e:
                    st.error(f"エラー: {e}")

    # ── メーカーTOPスキャン ──────────────────────────────────────────────────
    with scan_tab_maker:
        st.caption(
            "メーカーのTOPページURLを入力すると、配下の商品ページを自動検出して"
            "すべての車種情報をまとめてグラフに登録します。"
        )
        with st.expander("URLの例（Honda）", expanded=False):
            st.markdown("""
**メーカーTOP URL**
```
https://www.honda.co.jp/auto/?from=auto_header
```
このURLのページに含まれる車種リンク（例: /INSIGHT/, /FIT/, /VEZEL/ など）を自動検出します。
""")

        wm_url = st.text_input(
            "メーカーTOP URL",
            placeholder="例: https://www.honda.co.jp/auto/",
            key="web_maker_url",
        )

        wm_col1, wm_col2 = st.columns(2)
        with wm_col1:
            wm_max = st.number_input(
                "最大スキャン車種数", min_value=1, max_value=25, value=10,
                key="web_maker_max",
            )
        with wm_col2:
            wm_graph = st.checkbox("スキャン後にグラフも更新する", value=True, key="web_maker_graph")

        # 車種検出（Claude不要・無料プレビュー）
        disc_col, scan_col = st.columns(2)
        with disc_col:
            if st.button("車種URLを検出（プレビュー）", key="web_maker_discover_btn",
                         disabled=not wm_url.strip()):
                with st.spinner("車種ページを検索中..."):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/rescan_web/discover",
                            json={"url": wm_url.strip()},
                            timeout=30,
                        )
                        if resp.ok:
                            r = resp.json()
                            st.session_state.web_discovered = r.get("vehicles", [])
                            if not st.session_state.web_discovered:
                                st.warning("車種ページが検出できませんでした。URLを確認してください。")
                        else:
                            st.error(resp.json().get("detail", resp.text))
                    except Exception as e:
                        st.error(f"エラー: {e}")

        # 検出結果プレビュー
        if "web_discovered" not in st.session_state:
            st.session_state.web_discovered = []

        if st.session_state.web_discovered:
            disc = st.session_state.web_discovered
            st.markdown(f"**検出された車種: {len(disc)} 件**")
            disc_rows = []
            for v in disc[:wm_max]:
                disc_rows.append({"車種名": v["model_name"], "URL": v["url"]})
            st.dataframe(disc_rows, use_container_width=True, hide_index=True)

        with scan_col:
            if st.button(
                f"上位 {wm_max} 車種をスキャン",
                type="primary",
                key="web_maker_scan_btn",
                disabled=not wm_url.strip(),
            ):
                n = int(wm_max)
                with st.spinner(
                    f"最大 {n} 車種をスキャン中... （1車種あたり30秒〜1分、合計 {n}〜{n*2} 分かかります）"
                ):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/rescan_web/maker",
                            json={
                                "url": wm_url.strip(),
                                "max_vehicles": n,
                                "update_graph": wm_graph,
                            },
                            timeout=600,
                        )
                        if resp.ok:
                            r = resp.json()
                            succeeded = r.get("succeeded", [])
                            failed = r.get("failed", [])
                            st.success(
                                f"✅ スキャン完了！  "
                                f"成功: **{len(succeeded)} 車種**  "
                                f"（登録済み合計: {r.get('total_model_count', '?')} 車種）"
                            )
                            if succeeded:
                                st.markdown(
                                    "**登録済み車種:** "
                                    + "  /  ".join(succeeded)
                                )
                            if failed:
                                st.warning(f"取得失敗: {', '.join(failed)}")
                            if r.get("graph_steps"):
                                gsteps = r["graph_steps"]
                                if all(v == "ok" for v in gsteps.values()):
                                    st.caption("グラフ更新: ✓ 完了")
                                else:
                                    st.caption(f"グラフ更新（一部エラー）: {gsteps}")
                            # 検出キャッシュをクリア
                            st.session_state.web_discovered = []
                        else:
                            st.error(resp.json().get("detail", resp.text))
                    except requests.exceptions.ConnectionError:
                        st.error("APIサーバーに接続できません。")
                    except Exception as e:
                        st.error(f"エラー: {e}")

    # ── URLリスト一括スキャン ────────────────────────────────────────────────
    with scan_tab_list:
        st.caption(
            "JSレンダリングのサイト（Honda など）ではメーカーTOP自動検出が機能しない場合があります。"
            "その場合はここに車種名とURLを入力して一括スキャンしてください。"
        )

        with st.expander("入力フォーマットの説明", expanded=False):
            st.markdown("""
**1行 = 1車種** で以下のいずれかの形式で入力してください:

```
車種名, URL
INSIGHT, https://www.honda.co.jp/INSIGHT/
N-BOX, https://www.honda.co.jp/N-BOX/
FIT, https://www.honda.co.jp/FIT/
```

またはタブ区切り:
```
VEZEL	https://www.honda.co.jp/VEZEL/
CR-V	https://www.honda.co.jp/CR-V/
```

車種名を省略するとURLの末尾セグメントを車種名として使用します:
```
https://www.honda.co.jp/CIVIC/
https://www.honda.co.jp/ACCORD/
```
""")

        wl_text = st.text_area(
            "車種名 + URL リスト（1行1車種）",
            height=280,
            placeholder=(
                "INSIGHT, https://www.honda.co.jp/INSIGHT/\n"
                "N-BOX, https://www.honda.co.jp/N-BOX/\n"
                "FIT, https://www.honda.co.jp/FIT/\n"
                "VEZEL, https://www.honda.co.jp/VEZEL/\n"
                "N-ONE, https://www.honda.co.jp/N-ONE/\n"
                "FREED, https://www.honda.co.jp/FREED/"
            ),
            key="web_list_text",
        )
        wl_graph = st.checkbox("スキャン後にグラフも更新する", value=True, key="web_list_graph")

        def _parse_url_list(raw_text: str) -> list[dict]:
            """テキストを車種名+URLのリストに変換する。"""
            items = []
            for line in raw_text.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # カンマ区切り または タブ区切り
                if "," in line:
                    parts = [p.strip() for p in line.split(",", 1)]
                elif "\t" in line:
                    parts = [p.strip() for p in line.split("\t", 1)]
                else:
                    parts = ["", line.strip()]

                if len(parts) == 2 and parts[1].startswith("http"):
                    model_name = parts[0] or parts[1].rstrip("/").split("/")[-1].upper()
                    items.append({"model_name": model_name, "url": parts[1]})
                elif len(parts) == 1 and parts[0].startswith("http"):
                    url = parts[0]
                    model_name = url.rstrip("/").split("/")[-1].upper()
                    items.append({"model_name": model_name, "url": url})
            return items

        # プレビュー
        if wl_text.strip():
            parsed_items = _parse_url_list(wl_text)
            if parsed_items:
                st.markdown(f"**解析結果プレビュー: {len(parsed_items)} 車種**")
                st.dataframe(
                    [{"車種名": it["model_name"], "URL": it["url"]} for it in parsed_items],
                    use_container_width=True, hide_index=True,
                )
            else:
                st.warning("有効な行が見つかりません。フォーマットを確認してください。")
        else:
            parsed_items = []

        n_list = len(parsed_items)
        if st.button(
            f"リストの {n_list} 車種をスキャン" if n_list > 0 else "スキャン実行",
            type="primary",
            key="web_list_scan_btn",
            disabled=(n_list == 0),
        ):
            with st.spinner(
                f"{n_list} 車種をスキャン中... "
                f"（1車種あたり30秒〜1分、合計 {n_list}〜{n_list*2} 分かかります）"
            ):
                try:
                    resp = requests.post(
                        f"{API_BASE}/rescan_web/url-list",
                        json={
                            "vehicles": parsed_items,
                            "update_graph": wl_graph,
                        },
                        timeout=600,
                    )
                    if resp.ok:
                        r = resp.json()
                        succeeded = r.get("succeeded", [])
                        failed = r.get("failed", [])
                        st.success(
                            f"✅ スキャン完了！  "
                            f"成功: **{len(succeeded)} 車種**  "
                            f"（登録済み合計: {r.get('total_model_count', '?')} 車種）"
                        )
                        if succeeded:
                            st.markdown("**登録済み車種:** " + "  /  ".join(succeeded))
                        if failed:
                            st.warning(f"取得失敗: {', '.join(failed)}")
                        if r.get("graph_steps"):
                            gsteps = r["graph_steps"]
                            st.caption(
                                "グラフ更新: ✓ 完了"
                                if all(v == "ok" for v in gsteps.values())
                                else f"グラフ更新（一部エラー）: {gsteps}"
                            )
                    else:
                        st.error(resp.json().get("detail", resp.text))
                except requests.exceptions.ConnectionError:
                    st.error("APIサーバーに接続できません。")
                except Exception as e:
                    st.error(f"エラー: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Tab 4: Knowledge Graph — Consumer Area ⟷ Product Area
# ═══════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<p class="section-label">Knowledge Graph Explorer</p>', unsafe_allow_html=True)
    st.caption(
        "Consumer Area の絞り込み条件に合致するConsumerに"
        "リレーションのあるデータを、左右のエリアに分けてスコア順に表示します。"
        "項目を選択すると他の項目の選択肢が自動で絞り込まれます。"
    )

    # ── フィルター値取得 ──────────────────────────────────────────────────
    _, col_fy = st.columns([3, 1])
    with col_fy:
        if st.button("フィルター値を取得", use_container_width=True, key="kg_load_fv"):
            try:
                r = requests.get(f"{API_BASE}/graph/filter-values", timeout=15)
                if r.ok:
                    st.session_state.kg_filter_values = r.json()
                    st.success("フィルター値を取得しました。")
                else:
                    try:
                        detail = r.json().get("detail", r.text)
                    except Exception:
                        detail = r.text
                    st.error(detail)
            except requests.exceptions.ConnectionError:
                st.error(
                    f"APIサーバー（{API_BASE}）に接続できません。"
                    "別ターミナルで uvicorn を起動してください。"
                )
            except Exception as e:
                st.error(f"エラー: {e}")

    fv = st.session_state.kg_filter_values
    consumer_fv = fv.get("consumer", {})
    grades_by_vehicle = fv.get("grades_by_vehicle", {})

    # ── 2列レイアウト: Consumer Area | Product Area ──────────────────────
    col_c, col_p = st.columns([5, 4])

    with col_c:
        st.markdown(
            '<div style="margin-bottom:12px;">'
            '<span class="area-badge-consumer">Consumer Area</span></div>',
            unsafe_allow_html=True,
        )

        with st.expander("Consumer 属性フィルター", expanded=True):
            cr1, cr2 = st.columns(2)
            with cr1:
                f_gender  = st.multiselect("性別",         consumer_fv.get("gender", []),            key="kg_gender",  on_change=_update_kg_filters)
                f_age     = st.multiselect("年代",         consumer_fv.get("age_group", []),         key="kg_age",     on_change=_update_kg_filters)
                f_loc     = st.multiselect("都道府県",     consumer_fv.get("location", []),          key="kg_loc",     on_change=_update_kg_filters)
                f_country = st.multiselect("国",           consumer_fv.get("country", []),           key="kg_country", on_change=_update_kg_filters)
            with cr2:
                f_occ = st.multiselect("職業",         consumer_fv.get("occupation", []),        key="kg_occ", on_change=_update_kg_filters)
                f_inc = st.multiselect("年収帯",       consumer_fv.get("income_range", []),      key="kg_inc", on_change=_update_kg_filters)
                f_drv = st.multiselect("運転頻度",     consumer_fv.get("driving_frequency", []), key="kg_drv", on_change=_update_kg_filters)
                f_mob = st.multiselect("移動パターン", consumer_fv.get("mobility_pattern", []),  key="kg_mob", on_change=_update_kg_filters)

        with st.expander("意思決定ノード フィルター", expanded=True):
            # 行1: DecisionStyle | LifeEvent
            nr0a, nr0b = st.columns(2)
            with nr0a:
                f_decision_style = st.multiselect("DecisionStyle（意思決定スタイル）", fv.get("decision_style", []), key="kg_ds",  on_change=_update_kg_filters)
            with nr0b:
                f_life_event     = st.multiselect("LifeEvent（ライフイベント）",       fv.get("life_event", []),     key="kg_le",  on_change=_update_kg_filters)
            # 行2: Trigger | Regret
            nr1a, nr1b = st.columns(2)
            with nr1a:
                f_trigger = st.multiselect("Trigger（購入きっかけ）", fv.get("trigger", []), key="kg_trigger", on_change=_update_kg_filters)
            with nr1b:
                f_regret  = st.multiselect("Regret（後悔・不満）",    fv.get("regret", []),  key="kg_regret",  on_change=_update_kg_filters)
            # 行3: Need | Sub-Need
            nr2a, nr2b = st.columns(2)
            with nr2a:
                f_need        = st.multiselect("Need",               fv.get("need", []),                      key="kg_need",        on_change=_update_kg_filters)
            with nr2b:
                f_sub_need    = st.multiselect("Sub-Need",           fv.get("sub_need", []),                  key="kg_sub_need",    on_change=_update_kg_filters)
            # 行4: EvaluationCriteria | PurchaseDriver
            nr3a, nr3b = st.columns(2)
            with nr3a:
                f_ec          = st.multiselect("EvaluationCriteria", fv.get("evaluation_criteria", [])[:40],  key="kg_ec",          on_change=_update_kg_filters)
            with nr3b:
                f_pd          = st.multiselect("PurchaseDriver",     fv.get("purchase_driver", []),            key="kg_pd",          on_change=_update_kg_filters)

    with col_p:
        st.markdown(
            '<div style="margin-bottom:12px;">'
            '<span class="area-badge-product">Product Area</span></div>',
            unsafe_allow_html=True,
        )

        with st.expander("製品フィルター", expanded=True):
            f_vm = st.multiselect("VehicleModel", fv.get("vehicle_model", [])[:50], key="kg_vm", on_change=_update_kg_filters)

            # Grade multiselect（選択車種に絞り込み、クライアントサイドフィルター）
            _grade_opts: list[str] = []
            if f_vm:
                for _vm in f_vm:
                    for _g in grades_by_vehicle.get(_vm, []):
                        if _g not in _grade_opts:
                            _grade_opts.append(_g)
            else:
                for _gs in grades_by_vehicle.values():
                    for _g in _gs:
                        if _g not in _grade_opts:
                            _grade_opts.append(_g)
            f_grade   = st.multiselect("Grade",        _grade_opts,                       key="kg_grade")
            f_feature = st.multiselect("Feature",      fv.get("feature", [])[:50],        key="kg_feature", on_change=_update_kg_filters)

    # ── 分析実行 ──────────────────────────────────────────────────────────
    if st.button("分析実行", type="primary", use_container_width=True, key="kg_explore"):
        with st.spinner("グラフを集計中..."):
            payload = {
                "gender":              f_gender,
                "age_group":           f_age,
                "location":            f_loc,
                "country":             f_country,
                "occupation":          f_occ,
                "income_range":        f_inc,
                "driving_frequency":   f_drv,
                "mobility_pattern":    f_mob,
                "decision_style":      f_decision_style,
                "life_event":          f_life_event,
                "regret":              f_regret,
                "trigger":             f_trigger,
                "need":                f_need,
                "sub_need":            f_sub_need,
                "evaluation_criteria": f_ec,
                "purchase_driver":     f_pd,
                "vehicle_model":       f_vm,
                "feature":             f_feature,
            }
            try:
                r = requests.post(f"{API_BASE}/graph/explorer", json=payload, timeout=30)
                if r.ok:
                    st.session_state.kg_explorer_results = r.json()
                    st.rerun()
                else:
                    st.error(r.json().get("detail", r.text))
            except Exception as e:
                st.error(f"エラー: {e}")

    # ── 結果表示（Consumer Area 左 | Bridge 中央 | Product Area 右）────────
    kg_res = st.session_state.kg_explorer_results
    if kg_res is not None:
        cnt = kg_res.get("consumer_count", 0)
        if cnt == 0:
            st.warning("条件に合致するデータがありません。フィルターを緩めてください。")
        else:
            results = kg_res.get("results", {})
            _CONSUMER_NODES = ["DecisionStyle", "LifeEvent", "Trigger",
                               "Need", "Sub-Need", "EvaluationCriteria",
                               "PurchaseDriver", "Regret"]
            _PRODUCT_NODES  = ["VehicleModel", "Feature"]

            res_c, res_p = st.columns([5, 4])

            with res_c:
                st.markdown(
                    '<div style="margin-bottom:10px;">'
                    '<span class="area-badge-consumer">Consumer Area — 結果</span></div>',
                    unsafe_allow_html=True,
                )
                for key in _CONSUMER_NODES:
                    items = results.get(key)
                    if not items:
                        continue
                    rows_html = "".join(
                        f'<div class="explorer-row">'
                        f'<span class="explorer-name">{it["name"]}</span>'
                        f'<span class="explorer-score">{it["score"]}</span>'
                        f'</div>'
                        for it in items[:15]
                    )
                    st.markdown(
                        f'<div class="explorer-node-card" style="margin-bottom:10px;">'
                        f'<div class="explorer-type-label">{key}</div>'
                        f'{rows_html}</div>',
                        unsafe_allow_html=True,
                    )

            with res_p:
                st.markdown(
                    '<div style="margin-bottom:10px;">'
                    '<span class="area-badge-product">Product Area — 結果</span></div>',
                    unsafe_allow_html=True,
                )

                # VehicleModel + グレード
                vm_items = results.get("VehicleModel")
                if vm_items:
                    vm_rows_html = ""
                    for it in vm_items[:15]:
                        vname = it["name"]
                        grades = grades_by_vehicle.get(vname, [])
                        grade_tags = (
                            '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:3px;">'
                            + "".join(f'<span class="grade-badge-sm">{g}</span>' for g in grades)
                            + "</div>"
                        ) if grades else ""
                        vm_rows_html += (
                            f'<div class="explorer-row-vehicle">'
                            f'<div style="display:flex;width:100%;justify-content:space-between;">'
                            f'<span class="explorer-name">{vname}</span>'
                            f'<span class="explorer-score">{it["score"]}</span></div>'
                            f'{grade_tags}</div>'
                        )
                    st.markdown(
                        f'<div class="explorer-node-card" style="margin-bottom:10px;">'
                        f'<div class="explorer-type-label">VehicleModel &amp; Grade</div>'
                        f'{vm_rows_html}</div>',
                        unsafe_allow_html=True,
                    )

                # Feature
                feat_items = results.get("Feature")
                if feat_items:
                    rows_html = "".join(
                        f'<div class="explorer-row">'
                        f'<span class="explorer-name">{it["name"]}</span>'
                        f'<span class="explorer-score">{it["score"]}</span>'
                        f'</div>'
                        for it in feat_items[:15]
                    )
                    st.markdown(
                        f'<div class="explorer-node-card" style="margin-bottom:10px;">'
                        f'<div class="explorer-type-label">Feature</div>'
                        f'{rows_html}</div>',
                        unsafe_allow_html=True,
                    )

    st.divider()

    # ── グラフメンテナンス ────────────────────────────────────────────────
    with st.expander("グラフメンテナンス", expanded=False):
        st.caption(
            "KGデータ検証で修正・反映後に、参照されなくなったノードが選択肢に残ることがあります。"
            "「孤立ノードを削除」で整理できます（Trigger / LifeEvent / DecisionStyle / "
            "PurchaseDriver / EvaluationCriteria / Regret / VehicleOwnership が対象）。"
        )
        if st.button("孤立ノードを削除", key="kg_cleanup_btn",
                     help="どのConsumerからも参照されていないノードを削除します"):
            with st.spinner("孤立ノードを削除中..."):
                try:
                    resp = requests.post(f"{API_BASE}/graph/cleanup-orphans", timeout=30)
                    if resp.ok:
                        d = resp.json()
                        if d["deleted_total"] > 0:
                            detail = "、".join(f"{k}: {v}件" for k, v in d["deleted"].items())
                            st.success(f"✅ {d['deleted_total']} 件削除しました（{detail}）")
                        else:
                            st.info("削除対象の孤立ノードはありませんでした。")
                    else:
                        st.error(resp.text)
                except Exception as e:
                    st.error(f"エラー: {e}")

    # ── グラフ統計 ────────────────────────────────────────────────────────
    with st.expander("グラフ統計", expanded=False):
        if st.button("統計を更新", key="kg_stats_btn"):
            try:
                stats = requests.get(f"{API_BASE}/graph/stats", timeout=10).json()
                st.session_state.graph_stats = stats
            except Exception as e:
                st.error(f"取得エラー: {e}")

        if st.session_state.graph_stats:
            s = st.session_state.graph_stats
            nodes = s.get("nodes", {})
            rels  = s.get("relationships", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Consumer", nodes.get("Consumer", 0))
            c2.metric("VehicleModel (Lexus)", s.get("lexus_models", 0))
            c3.metric("Need", nodes.get("Need", 0))
            c4.metric("Feature", nodes.get("Feature", 0))
            col_n, col_r = st.columns(2)
            with col_n:
                st.write("**ノード**")
                for k, v in sorted(nodes.items(), key=lambda x: -x[1]):
                    st.write(f"  {k}: {v:,}")
            with col_r:
                st.write("**リレーション**")
                for k, v in sorted(rels.items(), key=lambda x: -x[1]):
                    st.write(f"  {k}: {v:,}")

    # ── 車種ノード一覧・SATISFIES 編集 ───────────────────────────────────
    with st.expander("SATISFIES リレーション編集", expanded=False):
        if st.button("車種一覧を取得", key="kg_load_vehicles"):
            try:
                vdata = requests.get(f"{API_BASE}/graph/vehicles", timeout=10).json()
                st.session_state.graph_vehicles = vdata.get("vehicles", [])
            except Exception as e:
                st.error(f"取得エラー: {e}")

        if st.session_state.graph_vehicles:
            vehicles = st.session_state.graph_vehicles
            rows = [{"モデル": v["name"], "カテゴリ": v.get("category",""),
                     "価格帯": v.get("price_range",""), "燃料": v.get("fuel_type",""),
                     "定員": v.get("seating",""), "ニーズ": ", ".join(v.get("needs",[])),
                     "Feature数": v.get("feature_count",0)} for v in vehicles]
            st.dataframe(rows, use_container_width=True)

            col_sv, col_sn, col_sa, col_sb = st.columns([2, 2, 1, 1])
            with col_sv:
                sel_vehicle = st.selectbox("車種", [v["name"] for v in vehicles], key="sat_vehicle")
            with col_sn:
                need_opts = ["safety","space","fuel_efficiency","comfort","design","technology","family","offroad"]
                sel_need = st.selectbox("ニーズ", need_opts, key="sat_need")
            with col_sa:
                st.write(""); st.write("")
                if st.button("追加", use_container_width=True, key="sat_add"):
                    r = requests.post(f"{API_BASE}/graph/satisfies",
                        json={"vehicle_name": sel_vehicle, "need_name": sel_need, "action": "add"}, timeout=10)
                    st.success(r.json().get("message","OK")) if r.ok else st.error(r.text)
            with col_sb:
                st.write(""); st.write("")
                if st.button("削除", use_container_width=True, key="sat_remove"):
                    r = requests.post(f"{API_BASE}/graph/satisfies",
                        json={"vehicle_name": sel_vehicle, "need_name": sel_need, "action": "remove"}, timeout=10)
                    st.success(r.json().get("message","OK")) if r.ok else st.error(r.text)

    # ── Cypher クエリ ─────────────────────────────────────────────────────
    with st.expander("Cypher クエリ実行（読み取り専用）", expanded=False):
        st.caption("MATCH / RETURN のみ。CREATE / SET / DELETE は Neo4j Browser を使用してください。")
        QUERY_PRESETS = {
            "-- プリセットを選択 --": "",
            "ノード統計": "MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count ORDER BY count DESC",
            "購入車種ランキング": "MATCH (c:Consumer)-[:SELECTED]->(v:VehicleModel) RETURN v.name AS model, count(c) AS buyers ORDER BY buyers DESC LIMIT 15",
            "ニーズ別 消費者数": "MATCH (c:Consumer)-[:HAS_NEED]->(n:Need) RETURN n.name AS need, count(c) AS consumers ORDER BY consumers DESC",
            "Lexus車種 × ニーズ": "MATCH (v:VehicleModel)-[:SATISFIES]->(n:Need) WHERE (v)-[:HAS_FEATURE]->() RETURN v.name AS model, collect(n.name) AS needs ORDER BY model",
            "満足度スコア付き購入": "MATCH (c:Consumer)-[r:SELECTED]->(v:VehicleModel) WHERE r.satisfaction_score IS NOT NULL RETURN v.name AS model, avg(r.satisfaction_score) AS avg_score, count(c) AS buyers ORDER BY avg_score DESC LIMIT 10",
            "家族4人以上の選択車種": "MATCH (c:Consumer)-[:SELECTED]->(v:VehicleModel) WHERE c.family_size >= 4 RETURN v.name AS model, count(c) AS count ORDER BY count DESC LIMIT 10",
        }
        preset = st.selectbox("プリセットクエリ", list(QUERY_PRESETS.keys()), key="cypher_preset")
        cypher_input = st.text_area("Cypher クエリ", value=QUERY_PRESETS[preset], height=100, key="cypher_input")
        if st.button("実行", type="primary", key="cypher_run"):
            if cypher_input.strip():
                with st.spinner("実行中..."):
                    try:
                        r = requests.post(f"{API_BASE}/graph/cypher", json={"query": cypher_input}, timeout=15)
                        if r.ok:
                            result = r.json()
                            st.caption(f"{result['count']} 件")
                            st.dataframe(result["rows"], use_container_width=True)
                        else:
                            st.error(r.json().get("detail", r.text))
                    except Exception as e:
                        st.error(f"エラー: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Tab 5: KGデータ検証
# ═══════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<p class="section-label">ナレッジグラフ変換精度 検証</p>', unsafe_allow_html=True)
    st.caption(
        "元ストーリーと抽出されたグラフノードを照合し、誤りを訂正します。"
        "訂正データは自動的に蓄積され、キーワードルールの改善提案に活用されます。"
    )

    # ── 進捗サマリー ─────────────────────────────────────────────────────
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s2:
        if st.button("進捗を更新", use_container_width=True, key="v_refresh_stats"):
            try:
                r = requests.get(f"{API_BASE}/verify/stats", timeout=10)
                if r.ok:
                    st.session_state.verify_stats = r.json()
            except Exception as e:
                st.error(f"エラー: {e}")
    with col_s3:
        if st.button("要修正を一括反映", use_container_width=True, key="v_apply_all",
                     help="要修正ステータスで未反映のストーリーをまとめてグラフに反映します"):
            with st.spinner("グラフに反映中..."):
                try:
                    resp = requests.post(f"{API_BASE}/verify/apply-all", timeout=120)
                    if resp.ok:
                        d = resp.json()
                        if d["applied_count"] > 0:
                            st.success(f"✅ {d['applied_count']} 件をグラフに反映しました")
                        else:
                            st.info("反映対象なし（未反映の要修正ストーリーがありません）")
                    else:
                        st.error(resp.text)
                except Exception as e:
                    st.error(f"エラー: {e}")

    if st.session_state.verify_stats:
        vs = st.session_state.verify_stats
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("総ストーリー数", vs["total_stories"])
        mc2.metric("検証済", vs["verified_count"])
        mc3.metric("要修正", vs["needs_correction"])
        mc4.metric("カバレッジ", f"{vs['coverage_pct']} %")

        acc = vs.get("accuracy", {})
        if acc:
            _FIELD_LABELS = {
                "trigger": "Trigger", "sub_trigger": "Sub-Trigger",
                "needs": "Needs", "sub_need": "Sub-Need",
                "evaluation_criteria": "評価基準",
                "purchase_driver": "購入ドライバー",
                "selected_vehicle": "購入車種", "grade": "グレード",
                "competitors": "競合車種",
            }
            st.write("**フィールド別正解率**")
            cols_a = st.columns(len(acc))
            for col, (fname, fdata) in zip(cols_a, acc.items()):
                rate  = fdata.get("rate")
                label = _FIELD_LABELS.get(fname, fname)
                val   = f"{int(rate*100)} %" if rate is not None else "未"
                col.metric(label, val,
                           delta=f"正{fdata['correct']} 誤{fdata['incorrect']}",
                           delta_color="off")
    else:
        st.info("「進捗を更新」ボタンで統計を取得してください。")

    st.divider()

    # ── ストーリー一覧 ────────────────────────────────────────────────────
    col_l1, col_l2, col_l3 = st.columns([2, 1, 1])
    with col_l1:
        status_filter = st.selectbox("表示フィルター", ["未検証のみ", "要修正のみ", "全件"], key="v_filter")
    with col_l2:
        st.write(""); st.write("")
        if st.button("ストーリー一覧を取得", use_container_width=True, key="v_load_list"):
            try:
                r = requests.get(f"{API_BASE}/verify/stories", timeout=15)
                if r.ok:
                    st.session_state.verify_stories  = r.json()["stories"]
                    st.session_state.verify_selected = None
                    st.session_state.verify_comparison = None
            except Exception as e:
                st.error(f"エラー: {e}")

    stories = st.session_state.verify_stories
    if stories:
        filter_map = {
            "未検証のみ": lambda s: s["status"] == "unverified",
            "要修正のみ": lambda s: s["status"] == "needs_correction",
            "全件":       lambda _: True,
        }
        filtered = [s for s in stories if filter_map[status_filter](s)]
        _STATUS_BADGE = {
            "unverified":       "未検証",
            "needs_correction": "要修正",
            "verified":         "検証済",
        }
        rows = [{"ステータス": _STATUS_BADGE.get(s["status"], s["status"]),
                 "グラフ反映": "✅反映済" if s.get("applied_at") else ("⚠️未反映" if s["status"] == "needs_correction" else "—"),
                 "ストーリーID": s["story_id"], "タイトル": s.get("title",""),
                 "車種": s.get("vehicle_model",""), "きっかけ": s.get("kikkake",""),
                 "検証日時": s.get("verified_at","")[:10],
                 "反映日時": s.get("applied_at","")[:10]} for s in filtered]
        st.caption(f"{len(filtered)} 件 / 全 {len(stories)} 件")
        st.dataframe(rows, use_container_width=True, height=200, hide_index=True, key="v_story_table")

        story_ids    = [s["story_id"] for s in filtered]
        story_labels = [
            f"[{_STATUS_BADGE.get(s['status'],'')}] {s['story_id']} — {s.get('title','')[:30]}"
            for s in filtered
        ]
        sel_idx = st.selectbox("検証するストーリーを選択", range(len(story_ids)),
                               format_func=lambda i: story_labels[i], key="v_story_sel")

        if st.button("このストーリーを検証", type="primary", key="v_load_story"):
            try:
                sid = story_ids[sel_idx]
                r = requests.get(f"{API_BASE}/verify/story/{sid}", timeout=10)
                if r.ok:
                    data = r.json()
                    st.session_state.verify_comparison = data
                    st.session_state.verify_selected   = sid
                    # 前回の検証結果でフォームウィジェットの初期値を復元
                    prev = data.get("previous_verification")
                    if prev and prev.get("fields"):
                        pfx = sid.replace("-", "_")
                        for fkey, fdata in prev["fields"].items():
                            is_ok    = fdata.get("is_correct", True)
                            corrected = fdata.get("corrected")
                            note      = fdata.get("note", "")
                            # ラジオボタン
                            st.session_state[f"vr_{pfx}_{fkey}"] = "正しい" if is_ok else "誤り"
                            # 修正値（誤りの場合）
                            if not is_ok and corrected is not None:
                                if isinstance(corrected, list):
                                    st.session_state[f"vm_{pfx}_{fkey}_multi"] = corrected
                                else:
                                    c_str = str(corrected)
                                    st.session_state[f"vs_{pfx}_{fkey}_sel"]  = c_str
                                    st.session_state[f"vt_{pfx}_{fkey}_free"] = c_str
                                    st.session_state[f"vt_{pfx}_{fkey}_text"] = c_str
                            # メモ
                            if note:
                                st.session_state[f"vn_{pfx}_{fkey}"] = note
                else:
                    st.error(r.json().get("detail", r.text))
            except Exception as e:
                st.error(f"エラー: {e}")

    # ── 検証フォーム ──────────────────────────────────────────────────────
    comp = st.session_state.verify_comparison
    if comp:
        sid  = st.session_state.verify_selected
        orig = comp["original"]
        ext  = comp["extracted"]
        trigger_cats      = comp.get("trigger_categories", comp.get("sub_trigger_categories", []))
        life_event_cats   = comp.get("life_event_categories", [])
        decision_styles   = comp.get("decision_style_options", [])
        regret_cats       = comp.get("regret_categories", [])
        pd_cats           = comp.get("purchase_driver_categories", [])
        vehicle_grades    = comp.get("vehicle_grades", [])
        all_sub_needs     = comp.get("all_sub_needs", [])
        all_eval_criteria = comp.get("all_eval_criteria", [])

        _NEEDS_ALL = ["safety", "space", "fuel_efficiency", "comfort", "design",
                      "technology", "family", "offroad"]

        st.divider()
        st.subheader(f"検証: {orig.get('title','')}  （{sid}）")

        # 前回の検証状態バナー
        prev_verif = comp.get("previous_verification")
        if prev_verif:
            prev_at = prev_verif.get("verified_at", "")[:10]
            prev_fields = prev_verif.get("fields", {})
            err_count = sum(1 for f in prev_fields.values() if not f.get("is_correct", True))
            if err_count:
                st.warning(
                    f"⚠️ 前回の検証（{prev_at}）で **{err_count} フィールドに誤り** が記録されています。"
                    f"  前回の訂正値を復元しました。確認・修正のうえ「検証結果を保存」してください。",
                    icon=None,
                )
            else:
                st.success(
                    f"✅ 前回の検証（{prev_at}）では全フィールド正解でした。再検証する場合は内容を確認してください。",
                    icon=None,
                )

        # 元テキスト 4 フィールドをまとめて表示
        with st.expander("元ストーリーテキストを表示（全文）", expanded=False):
            for label, key in [
                ("購入のきっかけ（purchase_trigger）", "purchase_trigger"),
                ("ご購入までのエピソード・ストーリー（purchase_story）", "purchase_story"),
                ("決め手（deciding_factor）", "deciding_factor"),
                ("同じクルマを検討している人へのアドバイス（advice）", "advice"),
            ]:
                val = orig.get(key, "")
                if val:
                    st.markdown(f"**{label}**")
                    st.markdown(
                        f'<div style="background:#F8F9FA;border:1px solid #CBD5E1;'
                        f'border-radius:4px;padding:10px 14px;color:#0D1B2A;'
                        f'font-size:13px;line-height:1.75;white-space:pre-wrap;'
                        f'word-wrap:break-word;margin-bottom:12px;">{val}</div>',
                        unsafe_allow_html=True,
                    )

        # ── 検証フォーム（st.form を使わず動的表示） ─────────────────────────
        st.write("各フィールドの抽出結果を確認し、誤りがあれば訂正してください。")
        field_results: dict = {}

        # helper: ラジオ + 修正 UI（フォーム外なのでラジオ変更で即リラン）
        def _verify_field(label, key, extracted_val, source_text,
                          options=None, is_list=False, form_key_prefix=""):
            st.markdown(f"**{label}**")
            st.markdown(
                f'<span class="verify-extracted">'
                f'{"、".join(extracted_val) if isinstance(extracted_val, list) else extracted_val}'
                f'</span>', unsafe_allow_html=True
            )
            ok = st.radio("正誤", ["正しい", "誤り"],
                          key=f"vr_{form_key_prefix}_{key}", horizontal=True)
            corrected = None
            note = ""
            if ok == "誤り":
                if options and not is_list:
                    # 既存リスト + 自由入力
                    opts_with_free = ["（リストから選択）"] + options + ["その他（自由入力）"]
                    sel = st.selectbox("正しい値を選択", opts_with_free,
                                       key=f"vs_{form_key_prefix}_{key}_sel")
                    if sel == "その他（自由入力）":
                        corrected = st.text_input("正しい値（自由入力）",
                                                   key=f"vt_{form_key_prefix}_{key}_free")
                    elif sel != "（リストから選択）":
                        corrected = sel
                elif options and is_list:
                    # マルチセレクト + 自由入力
                    # session_state に前回の修正値があればそちらを優先（default は未設定時のみ有効）
                    _ms_key = f"vm_{form_key_prefix}_{key}_multi"
                    _ms_default = [v for v in (extracted_val or []) if v in options]
                    corrected_list = st.multiselect(
                        "正しい値を選択", options,
                        default=_ms_default if _ms_key not in st.session_state else None,
                        key=_ms_key)
                    extra = st.text_input("追加（カンマ区切り）", key=f"vt_{form_key_prefix}_{key}_extra")
                    corrected = corrected_list + [x.strip() for x in extra.split(",") if x.strip()]
                else:
                    # 自由入力のみ
                    dv = ", ".join(extracted_val) if isinstance(extracted_val, list) else (extracted_val or "")
                    corrected = st.text_input("正しい値", value=dv,
                                               key=f"vt_{form_key_prefix}_{key}_text")
                note = st.text_input("メモ（任意）", key=f"vn_{form_key_prefix}_{key}")
            return {
                "extracted":   extracted_val,
                "is_correct":  ok == "正しい",
                "corrected":   corrected,
                "source_text": source_text[:400] if source_text else "",
                "note":        note,
            }

        pfx = sid.replace("-", "_")

        # 1. LifeEvent
        st.markdown("---")
        st.markdown("#### 1. LifeEvent（ライフイベント）")
        st.caption("消費者の購入背景となった長期的な生活変化（child_birth / marriage 等）")
        field_results["life_event"] = _verify_field(
            "抽出値", "life_event",
            ext.get("life_event") or "（なし）",
            orig.get("kikkake",""),
            options=life_event_cats, form_key_prefix=pfx
        )

        # 2. Trigger
        st.markdown("---")
        st.markdown("#### 2. Trigger（購入きっかけ）")
        st.caption(f"元データ（kikkake）: {orig.get('kikkake','（なし）')}")
        field_results["trigger"] = _verify_field(
            "抽出値", "trigger", ext.get("trigger","（なし）"),
            orig.get("kikkake",""),
            options=trigger_cats, form_key_prefix=pfx
        )

        # 3. DecisionStyle
        st.markdown("---")
        st.markdown("#### 3. DecisionStyle（意思決定スタイル）")
        st.caption("Maximizer=徹底比較型 / Satisficer=十分型 / Authority-driven=権威依存型 / Delegator=委任型 / Intuitive=直感型 / Impulsive=衝動型")
        field_results["decision_style"] = _verify_field(
            "抽出値", "decision_style",
            ext.get("decision_style") or "（未分類）",
            orig.get("purchase_story","") + orig.get("deciding_factor",""),
            options=decision_styles, form_key_prefix=pfx
        )

        # 4. Needs
        st.markdown("---")
        st.markdown("#### 4. Needs（ニーズカテゴリ）")
        st.caption("consumer_decisions.json から取得（LLM抽出済み）")
        field_results["needs"] = _verify_field(
            "抽出値", "needs", ext.get("needs", []),
            "", options=_NEEDS_ALL, is_list=True, form_key_prefix=pfx
        )

        # 5. Sub-Need
        st.markdown("---")
        st.markdown("#### 5. Sub-Need（詳細ニーズ）")
        st.caption("グラフから抽出（HAS_NEED → Need {level: 'child'}）")
        field_results["sub_need"] = _verify_field(
            "抽出値", "sub_need", ext.get("sub_need", []),
            "", options=all_sub_needs, is_list=True, form_key_prefix=pfx
        )

        # 6. EvaluationCriteria
        st.markdown("---")
        st.markdown("#### 6. 評価基準（EvaluationCriteria）")
        st.caption("グラフから抽出（VALUED → EvaluationCriteria）")
        field_results["evaluation_criteria"] = _verify_field(
            "抽出値", "evaluation_criteria", ext.get("evaluation_criteria", []),
            "", options=all_eval_criteria, is_list=True, form_key_prefix=pfx
        )

        # 7. PurchaseDriver
        st.markdown("---")
        st.markdown("#### 7. 購入ドライバー（PurchaseDriver）")
        src_pd = orig.get("deciding_factor","") or orig.get("most_satisfied","")
        st.caption(f"分類元テキスト（deciding_factor / most_satisfied）: {src_pd[:100]}...")
        pd_val = ext.get("purchase_driver", [])
        if isinstance(pd_val, str):
            pd_val = [pd_val] if pd_val and pd_val != "（なし）" else []
        field_results["purchase_driver"] = _verify_field(
            "抽出値", "purchase_driver", pd_val,
            src_pd, options=pd_cats, is_list=True, form_key_prefix=pfx
        )

        # 8. Selected vehicle
        st.markdown("---")
        st.markdown("#### 8. 購入車種（SELECTED）")
        st.caption(f"元データ（vehicle_model）: {orig.get('vehicle_model','（なし）')}")
        field_results["selected_vehicle"] = _verify_field(
            "抽出値", "selected_vehicle", ext.get("selected_vehicle","（なし）"),
            orig.get("vehicle_model",""), form_key_prefix=pfx
        )

        # 9. Grade
        st.markdown("---")
        st.markdown("#### 9. グレード（SELECTED グレード）")
        st.caption(f"元データ（grade）: {orig.get('grade','（なし）')}")
        field_results["grade"] = _verify_field(
            "抽出値", "grade", ext.get("grade","（なし）"),
            orig.get("grade",""),
            options=vehicle_grades if vehicle_grades else None,
            form_key_prefix=pfx
        )

        # 10. Competitors
        st.markdown("---")
        st.markdown("#### 10. 競合検討車種（CONSIDERED）")
        st.caption(f"元データ（considered_options）: {orig.get('considered_options', [])}")
        field_results["competitors"] = _verify_field(
            "抽出値", "competitors", ext.get("competitors", []),
            "", is_list=True, form_key_prefix=pfx
        )

        # 11. Regret
        st.markdown("---")
        st.markdown("#### 11. 後悔・不満（Regret）")
        st.caption("満足度が低い場合や不満の表現から抽出（severity: 1=軽微 / 2=中程度 / 3=重大）")
        regret_val = ext.get("regret", [])
        regret_display = (
            "、".join(
                f'{r.get("category","?")} (深刻度:{r.get("severity",1)}) — {r.get("description","")[:30]}'
                for r in regret_val
            ) if isinstance(regret_val, list) and regret_val else "（なし）"
        )
        field_results["regret"] = _verify_field(
            "抽出値", "regret", regret_display,
            orig.get("advice","") + " " + orig.get("purchase_story",""),
            form_key_prefix=pfx
        )

        # 保存 + グラフ反映
        st.markdown("---")
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            submitted_v = st.button("検証結果を保存", type="primary",
                                    use_container_width=True, key="v_save_btn")
        with btn_col2:
            apply_v = st.button("グラフに修正を反映", type="secondary",
                                use_container_width=True, key="v_apply_btn",
                                help="保存済みの訂正内容をNeo4jグラフに反映します（保存後に実行してください）")

        if submitted_v:
            payload_v = {
                "story_id":    sid,
                "verified_at": _dt.now().isoformat(timespec="seconds"),
                "fields":      field_results,
            }
            try:
                rv = requests.post(f"{API_BASE}/verify/story/{sid}", json=payload_v, timeout=10)
                if rv.ok:
                    error_count = sum(1 for f in field_results.values()
                                      if not f.get("is_correct", True))
                    if error_count:
                        st.warning(
                            f"保存しました。{error_count} フィールドに訂正あり。"
                            f"「グラフに修正を反映」ボタンでKGに反映してください。"
                        )
                    else:
                        st.success("保存しました。全フィールド正解です。")
                    r_s = requests.get(f"{API_BASE}/verify/stats", timeout=5)
                    if r_s.ok:
                        st.session_state.verify_stats = r_s.json()
                    st.rerun()
                else:
                    st.error(rv.json().get("detail", rv.text))
            except Exception as e:
                st.error(f"保存エラー: {e}")

        if apply_v:
            with st.spinner("Neo4j グラフに修正を反映中..."):
                try:
                    ra = requests.post(f"{API_BASE}/verify/story/{sid}/apply", timeout=30)
                    if ra.ok:
                        d = ra.json()
                        if d["applied"]:
                            st.success(
                                f"✅ グラフに反映しました。反映フィールド: "
                                f"{', '.join(d['applied'])}"
                            )
                        else:
                            st.info("反映する訂正がありません（全フィールド正解）。")
                    else:
                        st.error(ra.json().get("detail", ra.text))
                except Exception as e:
                    st.error(f"反映エラー: {e}")

    # ── 改善提案 ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("キーワードルール改善提案")
    st.caption(
        "訂正データを Claude が分析し、graph_builder.py のキーワード辞書への追加提案を生成します。"
        "訂正が蓄積されるほど提案の精度が上がります。"
    )
    if st.button("改善提案を生成（Claude 分析）", type="secondary", key="v_improve"):
        with st.spinner("Claude が誤分類パターンを分析中..."):
            try:
                ri = requests.post(f"{API_BASE}/verify/improvements", timeout=60)
                if ri.ok:
                    st.session_state.verify_improvements = ri.json()
                else:
                    st.error(ri.json().get("detail", ri.text))
            except Exception as e:
                st.error(f"エラー: {e}")

    imp = st.session_state.verify_improvements
    if imp:
        err_c = imp.get("error_count", 0)
        st.caption(f"分析対象の訂正ケース: {err_c} 件")
        summary = imp.get("summary", "")
        if summary:
            st.info(f"総評: {summary}")

        suggestions = imp.get("suggestions", [])
        if not suggestions:
            st.success(imp.get("message", "提案なし（訂正データが不足しています）"))
        else:
            for i, s in enumerate(suggestions, 1):
                field_lbl = {"sub_trigger": "Sub-Trigger", "purchase_driver": "購入ドライバー",
                             "trigger": "Trigger", "needs": "Needs"}.get(s.get("field",""), s.get("field",""))
                with st.expander(
                    f"提案 {i}: [{field_lbl}]  "
                    f"「{s.get('wrong_category','')}」→「{s.get('correct_category','')}」",
                    expanded=(i == 1),
                ):
                    st.write(f"**分析:** {s.get('analysis','')}")
                    if s.get("add_keywords"):
                        kws = ", ".join(f'`{k}`' for k in s["add_keywords"])
                        st.write(f"**追加推奨キーワード:** {kws}")
                    if s.get("reorder_hint"):
                        st.write(f"**順序ヒント:** {s['reorder_hint']}")
                    if s.get("story_ids"):
                        st.caption(f"関連ストーリー: {', '.join(s['story_ids'])}")
                    if s.get("add_keywords") and s.get("field") in ("sub_trigger", "purchase_driver"):
                        dict_name = ("_SUB_TRIGGER_CATEGORIES"
                                     if s["field"] == "sub_trigger"
                                     else "_PURCHASE_DRIVER_CATEGORIES")
                        cat      = s.get("correct_category", "?")
                        new_kws  = s["add_keywords"]
                        st.code(
                            f"# graph/graph_builder.py を更新\n"
                            f"{dict_name}[\"{cat}\"] += {new_kws}",
                            language="python",
                        )
