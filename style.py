"""
style.py

AI Home Manager için modern ve mobil uyumlu görünüm.
app.py ile aynı klasöre koy. Bu dosyanın TAMAMI eski style.py'nin yerine geçer.

Kullanım (app.py içinde):
    from style import apply_style, hero, sidebar_brand, bottom_nav
    st.set_page_config(...)
    apply_style()
"""

import html

import streamlit as st


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --hm-accent: #6366f1;
  --hm-accent-2: #8b5cf6;
  --hm-border: #e6e9f2;
  --hm-card: #ffffff;
  --hm-muted: #64748b;
  --hm-shadow: 0 1px 2px rgba(16,24,40,.04), 0 6px 16px rgba(16,24,40,.05);
}

/* ---------- YAZI TİPİ (ikon fontlarına dokunmaz) ---------- */
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp a,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp button, .stApp input, .stApp textarea, .stApp th, .stApp td,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"],
[data-testid="stCaptionContainer"] {
  font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif !important;
}

/* ---------- SAYFA DÜZENİ ---------- */
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px; }
header[data-testid="stHeader"] { background: transparent; }
footer, .stDeployButton, [data-testid="stDeployButton"] { display: none !important; }

h1 { font-weight: 800 !important; letter-spacing: -0.02em; }
h2, h3 { font-weight: 700 !important; letter-spacing: -0.01em; }
[data-testid="stCaptionContainer"] { color: var(--hm-muted); }

/* ---------- KARTLAR (border=True konteynerler ve formlar) ---------- */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stForm"] {
  border-radius: 16px !important;
  border-color: var(--hm-border) !important;
  background: var(--hm-card);
  box-shadow: var(--hm-shadow);
}

/* ---------- METRİKLER ---------- */
[data-testid="stMetricLabel"] p { color: var(--hm-muted); font-size: .82rem; font-weight: 500; }
[data-testid="stMetricValue"] { font-weight: 700; letter-spacing: -.02em; }
[data-testid="stMetricValue"] div { font-size: clamp(1.25rem, 1.7vw, 1.85rem); }
[data-testid="stMetricDelta"] { font-weight: 600; }

/* ---------- BUTONLAR ---------- */
.stButton > button, .stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button,
[data-testid^="stBaseButton"] {
  border-radius: 10px;
  font-weight: 600;
  transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
}
button[kind="secondary"], [data-testid="stBaseButton-secondary"] {
  background: #ffffff;
  border: 1px solid var(--hm-border);
  color: #1e293b;
}
button[kind="secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--hm-accent);
  color: var(--hm-accent);
  transform: translateY(-1px);
}
button[kind="primary"], button[kind="primaryFormSubmit"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, var(--hm-accent), var(--hm-accent-2)) !important;
  border: none !important;
  color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(99,102,241,.30);
}
button[kind="primary"] p, button[kind="primaryFormSubmit"] p,
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p {
  color: #ffffff !important;
}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(99,102,241,.35);
}

/* ---------- SIDEBAR ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #f5f3ff 0%, #eef2ff 55%, #f8fafc 100%);
  border-right: 1px solid var(--hm-border);
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255,255,255,.75);
  box-shadow: none;
}
[data-testid="stSidebar"] button[kind="secondary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
  background: transparent;
  border: none;
  box-shadow: none;
  color: #334155;
  padding: .55rem .9rem;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover,
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
  background: rgba(99,102,241,.10);
  color: var(--hm-accent);
  transform: none;
}
[data-testid="stSidebar"] button { justify-content: flex-start; text-align: left; }
[data-testid="stSidebar"] button > div { justify-content: flex-start; width: 100%; }
[data-testid="stSidebar"] button p { text-align: left; }

/* ---------- SEKMELER (hap görünümü) ---------- */
[data-baseweb="tab-list"] { gap: 6px; border-bottom: none !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }
button[data-baseweb="tab"] {
  border-radius: 999px;
  padding: .4rem 1.1rem;
  background: rgba(99,102,241,.07);
  font-weight: 600;
}
button[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, var(--hm-accent), var(--hm-accent-2));
}
button[data-baseweb="tab"][aria-selected="true"] p { color: #ffffff !important; }

/* ---------- DİĞER BİLEŞENLER ---------- */
[data-testid="stExpander"] {
  border-radius: 14px !important;
  border-color: var(--hm-border) !important;
  background: var(--hm-card);
}
[data-testid="stExpander"] summary { font-weight: 600; }
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
  border-radius: 10px !important;
}
[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stDataFrame"] {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--hm-border);
}
[data-testid="stProgress"] div[role="progressbar"] { border-radius: 999px; background: #e8ebf5; }
[data-testid="stProgress"] div[role="progressbar"] > div {
  background: linear-gradient(90deg, var(--hm-accent), var(--hm-accent-2)) !important;
  border-radius: 999px;
}
[data-testid="stChatMessage"] { border-radius: 14px; }

/* ---------- ÖZEL BİLEŞENLER ---------- */
.hm-hero {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 55%, #ec4899 130%);
  border-radius: 20px;
  padding: 1.6rem 1.8rem;
  color: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.2rem;
  box-shadow: 0 10px 30px rgba(99,102,241,.25);
}
.hm-hero-title { font-size: 1.9rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.2; }
.hm-hero-sub { opacity: .88; margin-top: .25rem; font-size: .95rem; }
.hm-hero-chip {
  background: rgba(255,255,255,.18);
  border: 1px solid rgba(255,255,255,.35);
  padding: .45rem .95rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: .9rem;
  white-space: nowrap;
}
.hm-brand { display: flex; align-items: center; gap: .7rem; padding: .2rem .2rem .6rem; }
.hm-brand-logo {
  width: 42px; height: 42px; border-radius: 12px;
  background: linear-gradient(135deg, var(--hm-accent), var(--hm-accent-2));
  display: flex; align-items: center; justify-content: center;
  font-size: 1.35rem;
  box-shadow: 0 6px 14px rgba(99,102,241,.35);
}
.hm-brand-name { font-weight: 800; letter-spacing: -.01em; line-height: 1.1; color: #0f172a; }
.hm-brand-sub { font-size: .75rem; color: var(--hm-muted); }

/* ---------- MOBİL ---------- */
div.st-key-bottom_nav { display: none !important; }

@media (max-width: 640px) {

  .block-container { padding: 1rem .75rem 6rem !important; }
  [data-testid="stVerticalBlock"] { gap: .7rem; }

  h1 { font-size: 1.6rem !important; }
  h2, h3 { font-size: 1.15rem !important; }

  .hm-hero { flex-direction: column; align-items: flex-start; padding: 1.1rem 1.2rem; border-radius: 16px; }
  .hm-hero-title { font-size: 1.45rem; }
  .hm-hero-sub { font-size: .85rem; }

  /* Metrik satırları: tek sütun yerine yan yana ikişerli */
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"] {
    min-width: calc(50% - .75rem) !important;
    flex: 1 1 calc(50% - .75rem) !important;
  }
  [data-testid="stMetricValue"] div { font-size: 1.25rem; }

  /* Takvim ızgarası telefonda sığmaz: gizlenir, altındaki liste görünür */
  [data-testid="stHorizontalBlock"]:has(.cal-head),
  [data-testid="stHorizontalBlock"]:has([class*="st-key-cal_day_"]) {
    display: none !important;
  }

  /* Parmakla dokunma: büyük butonlar, iOS'ta yakınlaşmayı önleyen yazı boyutu */
  .stButton > button, .stDownloadButton > button, [data-testid^="stBaseButton"] {
    min-height: 2.75rem;
  }
  input, textarea, [data-baseweb="select"] input { font-size: 16px !important; }
  button[data-baseweb="tab"] { padding: .35rem .8rem; font-size: .85rem; }

  /* Grafiklerde araç çubuğu dokunmatikte işe yaramaz */
  .js-plotly-plot .modebar-container { display: none !important; }

  /* Alt menü çubuğu */
  div.st-key-bottom_nav {
    display: flex !important;
    flex-direction: row;
    flex-wrap: nowrap;
    gap: 6px;
    position: fixed;
    left: 0; right: 0; bottom: 0;
    z-index: 999;
    padding: .45rem .6rem calc(.45rem + env(safe-area-inset-bottom, 0px));
    background: rgba(255,255,255,.96);
    backdrop-filter: blur(10px);
    border-top: 1px solid var(--hm-border);
    overflow-x: auto;
    box-shadow: 0 -4px 16px rgba(16,24,40,.06);
  }
  div.st-key-bottom_nav > div { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }
  div.st-key-bottom_nav button { white-space: nowrap; padding: .4rem .85rem; font-size: .82rem; }

  /* AI Asistan yazı kutusu alt menünün üstünde kalsın */
  [data-testid="stBottom"] { margin-bottom: 3.9rem; }
}
</style>
"""

# Boş satırlar Markdown ayrıştırıcısını bozmasın diye temizlenir.
_CSS = "\n".join(line for line in _CSS.splitlines() if line.strip())


def apply_style():
    """Tüm sayfalara görünümü uygular. set_page_config'ten sonra çağır."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title, subtitle="", chip=""):
    """Renkli sayfa başlığı bandı. chip: sağdaki küçük etiket (örn. tarih)."""
    chip_html = (
        f'<div class="hm-hero-chip">{html.escape(chip)}</div>' if chip else ""
    )

    st.markdown(
        '<div class="hm-hero"><div>'
        f'<div class="hm-hero-title">{html.escape(title)}</div>'
        f'<div class="hm-hero-sub">{html.escape(subtitle)}</div>'
        f'</div>{chip_html}</div>',
        unsafe_allow_html=True
    )


def sidebar_brand():
    """Sidebar'ın üstündeki logo ve uygulama adı."""
    st.sidebar.markdown(
        '<div class="hm-brand"><div class="hm-brand-logo">🏠</div><div>'
        '<div class="hm-brand-name">AI Home Manager</div>'
        '<div class="hm-brand-sub">Akıllı ev yönetimi</div>'
        '</div></div>',
        unsafe_allow_html=True
    )


def bottom_nav(items, badges, current):
    """Sadece telefonda görünen, kaydırılabilir alt menü çubuğu.
    items: NAV_ITEMS ([(anahtar, ikon, ad), ...])
    badges: {anahtar: sayı}
    current: açık sayfanın anahtarı"""

    with st.container(key="bottom_nav"):

        for i, (key, icon, label) in enumerate(items):

            badge = badges.get(key, 0)

            text = f"{icon} {label}" + (f" 🔴{badge}" if badge else "")

            if st.button(
                text,
                key=f"mnav_{i}",
                type="primary" if current == key else "secondary"
            ):
                st.session_state.menu = key
                st.rerun()