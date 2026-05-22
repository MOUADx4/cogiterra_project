"""
Dashboard Cogiterra Bounces — Edition 2026
===========================================
Design : bento grid, glassmorphism, micro-interactions.
Lancement : streamlit run dashboard/app.py
"""
from __future__ import annotations

import base64
import json
import random
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =============================================================================
# CONFIG
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "bounces.db"
USER_RULES_PATH = PROJECT_ROOT / "data" / "user_rules.json"
LOGO_PNG = PROJECT_ROOT / "dashboard" / "assets" / "cogiterra_logo.png"
LOGO_SVG = PROJECT_ROOT / "dashboard" / "assets" / "cogiterra_logo.svg"

CATEGORY_LABELS = {
    "hard_bounce":     "Hard bounce",
    "soft_bounce":     "Soft bounce",
    "address_change":  "Changement",
    "technical_error": "Technique",
    "unknown":         "Non classifié",
}
CATEGORY_COLORS = {
    "hard_bounce":     "#ef4444",
    "soft_bounce":     "#f59e0b",
    "address_change":  "#3b82f6",
    "technical_error": "#a855f7",
    "unknown":         "#64748b",
}
COST_PER_EMAIL_CENTS = 0.05

st.set_page_config(
    page_title="Cogiterra Bounces • Operations",
    page_icon=str(LOGO_PNG) if LOGO_PNG.exists() else "📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CSS — Design 2026
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,300..700,0..1,-25..200');

    /* Icônes Material Symbols (Lucide-like, professional) */
    .mi {
        font-family: 'Material Symbols Outlined';
        font-weight: 400; font-style: normal;
        font-size: 1.05em;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-feature-settings: 'liga';
        -webkit-font-smoothing: antialiased;
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        vertical-align: middle;
        color: #60a5fa;
        position: relative;
        top: -1px;
    }
    .mi-sm { font-size: 0.95em; }
    .mi-lg { font-size: 1.4em; }
    .mi-xl { font-size: 2.2em; top: 0; }
    .mi-white { color: #fafafa; }
    .mi-muted { color: #71717a; }
    .mi-green { color: #34d399; }
    .mi-amber { color: #fbbf24; }
    .mi-red    { color: #f87171; }
    .mi-violet { color: #c084fc; }
    .mi-fill { font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24; }

    /* Base typography */
    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, sans-serif !important;
        font-feature-settings: 'cv11', 'ss01', 'ss03', 'cv02';
    }

    /* Background : noir profond + grille subtile + halos colorés */
    .stApp {
        background:
            radial-gradient(circle at 15% 0%, rgba(59,130,246,0.10) 0%, transparent 35%),
            radial-gradient(circle at 85% 100%, rgba(168,85,247,0.10) 0%, transparent 40%),
            radial-gradient(circle at 50% 50%, rgba(16,185,129,0.04) 0%, transparent 50%),
            linear-gradient(180deg, #07080F 0%, #0a0a12 100%);
        background-attachment: fixed;
    }
    .stApp::before {
        content: ''; position: fixed; inset: 0; pointer-events: none;
        background-image:
            linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
        background-size: 48px 48px;
        z-index: 0;
    }
    .main .block-container { padding-top: 1.2rem; max-width: 1500px; }

    /* Hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* Typo hierarchy */
    h1 {
        color: #fafafa !important; font-weight: 800 !important;
        letter-spacing: -0.03em !important; font-size: 2.4rem !important;
        background: linear-gradient(135deg, #fafafa 0%, #94a3b8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    h2 { color: #f1f5f9 !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
    h3 { color: #e2e8f0 !important; font-weight: 600 !important; letter-spacing: -0.01em !important; }
    h4 { color: #cbd5e1 !important; font-weight: 600 !important; }
    p, .stMarkdown, label { color: #cbd5e1 !important; }
    .stCaption, [data-testid="stCaption"] { color: #71717a !important; font-size: 0.78rem !important; }
    code, .stCode, pre {
        font-family: 'JetBrains Mono', monospace !important;
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 6px !important;
    }

    /* === KPI CARDS (bento) === */
    [data-testid="stMetric"] {
        background:
            linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%);
        border: 1px solid rgba(255,255,255,0.07);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        padding: 1.5rem 1.4rem !important;
        border-radius: 20px !important;
        box-shadow:
            0 1px 0 rgba(255,255,255,0.06) inset,
            0 24px 60px -20px rgba(0,0,0,0.6);
        transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
        position: relative; overflow: hidden;
    }
    [data-testid="stMetric"]::before {
        content: ''; position: absolute; inset: 0;
        background: radial-gradient(circle at 100% 0%, rgba(59,130,246,0.08) 0%, transparent 50%);
        opacity: 0; transition: opacity 0.3s;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        border-color: rgba(255,255,255,0.14);
        box-shadow:
            0 1px 0 rgba(255,255,255,0.1) inset,
            0 32px 80px -16px rgba(0,0,0,0.7);
    }
    [data-testid="stMetric"]:hover::before { opacity: 1; }
    [data-testid="stMetricLabel"] {
        color: #71717a !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.12em !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #fafafa !important;
        font-size: 2.6rem !important;
        font-weight: 800 !important;
        font-variant-numeric: tabular-nums !important;
        letter-spacing: -0.03em !important;
        line-height: 1.1 !important;
    }
    [data-testid="stMetricDelta"] {
        color: #10b981 !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
    }

    /* === SIDEBAR === */
    [data-testid="stSidebar"] {
        background: rgba(8,8,15,0.72) !important;
        backdrop-filter: blur(40px) saturate(180%);
        -webkit-backdrop-filter: blur(40px) saturate(180%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    [data-testid="stSidebar"] .stMarkdown p { color: #a1a1aa !important; font-size: 0.85rem; }

    /* === BUTTONS === */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 1.2rem !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        letter-spacing: -0.01em !important;
        transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(59,130,246,0.25), 0 0 0 1px rgba(255,255,255,0.08) inset !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 24px rgba(59,130,246,0.4), 0 0 0 1px rgba(255,255,255,0.15) inset !important;
    }
    .stButton > button:active { transform: translateY(0); }
    .stDownloadButton > button {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        box-shadow: none !important;
    }

    /* === BADGES === */
    .badge {
        display: inline-flex; align-items: center; gap: 0.3rem;
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        font-variant-numeric: tabular-nums;
    }
    .badge-ok      { background: rgba(16,185,129,0.12); color: #34d399; border: 1px solid rgba(16,185,129,0.25); }
    .badge-warn    { background: rgba(245,158,11,0.12); color: #fbbf24; border: 1px solid rgba(245,158,11,0.25); }
    .badge-danger  { background: rgba(239,68,68,0.12);  color: #f87171; border: 1px solid rgba(239,68,68,0.25); }
    .badge-info    { background: rgba(59,130,246,0.12); color: #60a5fa; border: 1px solid rgba(59,130,246,0.25); }
    .badge-violet  { background: rgba(168,85,247,0.12); color: #c084fc; border: 1px solid rgba(168,85,247,0.25); }

    /* === PULSE === */
    .pulse-dot {
        display: inline-block; width: 7px; height: 7px;
        background: #10b981; border-radius: 50%;
        animation: pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    @keyframes pulse-ring {
        0%, 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.5); }
        50%      { box-shadow: 0 0 0 8px rgba(16,185,129,0); }
    }

    /* === BENTO PANEL === */
    .bento {
        background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015));
        border: 1px solid rgba(255,255,255,0.07);
        backdrop-filter: blur(24px);
        padding: 1.6rem;
        border-radius: 20px;
        box-shadow: 0 1px 0 rgba(255,255,255,0.06) inset, 0 24px 60px -20px rgba(0,0,0,0.6);
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .bento:hover {
        border-color: rgba(255,255,255,0.12);
        transform: translateY(-2px);
    }
    .bento-tight { padding: 1rem 1.2rem; }
    .bento h4 { margin: 0 0 0.6rem 0; font-size: 0.78rem; color: #71717a; text-transform: uppercase; letter-spacing: 0.1em; }
    .bento-value { font-size: 2.4rem; font-weight: 800; color: #fafafa; line-height: 1; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
    .bento-sub { font-size: 0.8rem; color: #71717a; margin-top: 0.4rem; }

    /* === INSIGHTS === */
    .insight {
        background: linear-gradient(135deg, rgba(59,130,246,0.08), rgba(139,92,246,0.04));
        border: 1px solid rgba(59,130,246,0.18);
        border-left: 3px solid #3b82f6;
        padding: 0.9rem 1.2rem;
        border-radius: 0 14px 14px 0;
        margin-bottom: 0.7rem;
        color: #e2e8f0 !important;
        font-size: 0.9rem;
    }
    .insight-warn { background: linear-gradient(135deg, rgba(245,158,11,0.08), rgba(239,68,68,0.04)); border-color: rgba(245,158,11,0.25); border-left-color: #f59e0b; }
    .insight-good { background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.04)); border-color: rgba(16,185,129,0.25); border-left-color: #10b981; }

    /* === TABS === */
    [data-baseweb="tab-list"] {
        gap: 6px !important;
        background: rgba(255,255,255,0.03) !important;
        padding: 6px !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255,255,255,0.05);
    }
    [data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 10px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
        font-size: 0.86rem !important;
        color: #94a3b8 !important;
        transition: all 0.2s ease !important;
    }
    [data-baseweb="tab"]:hover { background: rgba(255,255,255,0.04) !important; color: #e2e8f0 !important; }
    [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(59,130,246,0.95), rgba(139,92,246,0.95)) !important;
        color: white !important;
        box-shadow: 0 4px 14px rgba(59,130,246,0.3), 0 0 0 1px rgba(255,255,255,0.1) inset !important;
    }

    /* === DATAFRAMES === */
    .stDataFrame {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: rgba(255,255,255,0.02);
    }

    /* === RADIO & INPUTS === */
    .stRadio > div { gap: 0.5rem; }
    .stRadio label, .stMultiSelect label, .stTextInput label, .stSelectbox label {
        color: #94a3b8 !important; font-size: 0.78rem !important;
        text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
    }
    .stTextInput input, .stMultiSelect [data-baseweb="select"], .stSelectbox [data-baseweb="select"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 10px !important;
    }

    /* Toggle */
    [data-baseweb="checkbox"] { background: transparent !important; }

    /* Spinner */
    .stSpinner > div { color: #60a5fa !important; }

    /* Alerts */
    .stAlert {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 14px !important;
        color: #e2e8f0 !important;
    }

    /* Hide deploy button & menus */
    .stDeployButton { display: none !important; }

    /* Logo container */
    .logo-wrap {
        padding: 0.5rem 0 1rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        margin-bottom: 1rem;
    }

    /* Hover/highlights for live feed cards */
    .feed-card {
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.45rem;
        transition: all 0.2s ease;
    }
    .feed-card:hover {
        background: rgba(255,255,255,0.05);
        border-color: rgba(255,255,255,0.1);
        transform: translateX(2px);
    }

    /* Logo SVG color override (for inline SVG) */
    .logo-text { color: #fafafa; font-weight: 700; letter-spacing: -0.02em; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# HELPERS (inchangés)
# =============================================================================
@st.cache_data(ttl=5)
def load_data() -> dict:
    if not DB_PATH.exists():
        return {"result": pd.DataFrame(), "stats": pd.DataFrame(),
                "soft_counter": pd.DataFrame(), "counters": pd.DataFrame(),
                "suggestions": pd.DataFrame()}
    conn = sqlite3.connect(DB_PATH)
    try:
        result = pd.read_sql_query("SELECT * FROM result ORDER BY processed_at DESC", conn)
        stats = pd.read_sql_query("SELECT * FROM stats ORDER BY report_date DESC", conn)
        soft_counter = pd.read_sql_query("SELECT * FROM soft_bounce_counter ORDER BY failures DESC", conn)
        counters = pd.read_sql_query("SELECT * FROM counters", conn)
        try:
            suggestions = pd.read_sql_query(
                "SELECT * FROM rule_suggestions ORDER BY suggested_at DESC", conn)
        except Exception:
            suggestions = pd.DataFrame()
    finally:
        conn.close()
    return {"result": result, "stats": stats, "soft_counter": soft_counter,
            "counters": counters, "suggestions": suggestions}


def load_user_rules() -> list:
    if not USER_RULES_PATH.exists():
        return []
    try:
        return json.loads(USER_RULES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_user_rules(rules: list) -> None:
    USER_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_RULES_PATH.write_text(
        json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")


def adopt_suggestion(suggestion_id: int, pattern: str, category: str,
                     confidence: float, reason: str) -> bool:
    try:
        re.compile(pattern, re.IGNORECASE)
    except re.error:
        return False
    rules = load_user_rules()
    rules.append({
        "pattern": pattern, "category": category, "confidence": confidence,
        "reason": reason or "Apprise via dashboard",
        "adopted_at": datetime.now().isoformat(timespec="seconds"),
    })
    save_user_rules(rules)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE rule_suggestions SET status='adopted', decided_at=? WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), suggestion_id))
        conn.commit()
    finally:
        conn.close()
    return True


def reject_suggestion(suggestion_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE rule_suggestions SET status='rejected', decided_at=? WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), suggestion_id))
        conn.commit()
    finally:
        conn.close()


def inject_demo_data():
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS result (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email_address TEXT, category TEXT,
            confidence REAL, new_email TEXT, reason TEXT, method TEXT, processed_at TEXT);
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT, report_date TEXT UNIQUE,
            total_processed INTEGER, n_hard_bounce INTEGER, n_soft_bounce INTEGER,
            n_address_change INTEGER, n_technical INTEGER, n_unknown INTEGER,
            n_forwarded INTEGER, n_by_rules INTEGER, n_by_llm INTEGER,
            avg_confidence REAL, n_soft_above_threshold INTEGER,
            report_sent_at TEXT, report_sent_ok INTEGER);
        CREATE TABLE IF NOT EXISTS soft_bounce_counter (
            email_address TEXT PRIMARY KEY, failures INTEGER, last_failure TEXT);
        CREATE TABLE IF NOT EXISTS rule_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, pattern TEXT, category TEXT,
            confidence REAL, sample_email TEXT, sample_text TEXT,
            llm_reason TEXT, suggested_at TEXT, status TEXT DEFAULT 'pending',
            decided_at TEXT);
    """)
    cur.execute("DELETE FROM stats")
    for i in range(30):
        d = (datetime.now() - timedelta(days=29 - i)).strftime("%Y-%m-%d")
        base = random.randint(150, 280)
        h = int(base * random.uniform(0.55, 0.70))
        s = int(base * random.uniform(0.25, 0.38))
        c = random.randint(0, 5)
        t = random.randint(0, 3)
        u = base - h - s - c - t
        rules = int(base * random.uniform(0.75, 0.92))
        llm = base - rules
        cur.execute("""INSERT INTO stats (report_date, total_processed, n_hard_bounce,
            n_soft_bounce, n_address_change, n_technical, n_unknown,
            n_forwarded, n_by_rules, n_by_llm, avg_confidence, n_soft_above_threshold,
            report_sent_at, report_sent_ok) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d, base, h, s, c, t, max(u, 0), random.randint(2, 12), rules, llm,
             round(random.uniform(0.82, 0.96), 2), random.randint(0, 8),
             f"{d}T06:05:00", 1))

    cur.execute("DELETE FROM result")
    domains = ["gmail.com", "yahoo.fr", "outlook.com", "orange.fr", "free.fr",
               "wanadoo.fr", "hotmail.fr", "laposte.net", "sfr.fr", "bbox.fr"]
    names = ["jean.dupont", "marie.martin", "paul.durand", "claire.rousseau",
             "antoine.lefebvre", "sophie.bernard", "luc.moreau", "emma.petit",
             "thomas.richard", "julie.thomas", "pierre.dubois", "alice.moreau"]
    reasons_hard = ["SMTP 5.1.1 user unknown", "SMTP 5.1.2 domain not found",
                    "No longer valid", "Account disabled", "Mailbox unavailable"]
    reasons_soft = ["Mailbox full", "Quota exceeded", "Out of office",
                    "Temporarily unavailable", "En conge jusqu'au 30/05"]
    now = datetime.now()
    for i in range(60):
        email = f"{random.choice(names)}{random.randint(1,99)}@{random.choice(domains)}"
        r = random.random()
        if r < 0.55:
            cat, conf = "hard_bounce", random.uniform(0.88, 0.99)
            reason = random.choice(reasons_hard); method = "rules" if random.random() < 0.85 else "llm"
            new_email = None
        elif r < 0.85:
            cat, conf = "soft_bounce", random.uniform(0.80, 0.95)
            reason = random.choice(reasons_soft); method = "rules" if random.random() < 0.75 else "llm"
            new_email = None
        elif r < 0.95:
            cat, conf = "address_change", random.uniform(0.85, 0.98)
            reason = "Nouvelle adresse detectee"; method = "llm"
            new_email = f"{email.split('@')[0]}@nouveau-domaine.fr"
        else:
            cat, conf = "unknown", 0.0
            reason = "Aucune regle ne correspond"; method = "rules"
            new_email = None
        ts = (now - timedelta(minutes=random.randint(0, 480))).strftime("%Y-%m-%dT%H:%M:%S")
        cur.execute("""INSERT INTO result (email_address, category, confidence,
            new_email, reason, method, processed_at) VALUES (?,?,?,?,?,?,?)""",
            (email, cat, round(conf, 2), new_email, reason, method, ts))

    cur.execute("DELETE FROM soft_bounce_counter")
    for i in range(25):
        email = f"{random.choice(names)}{random.randint(1,99)}@{random.choice(domains)}"
        fails = random.choices([1, 2, 3, 4, 5, 6, 7], weights=[30, 25, 15, 10, 8, 7, 5])[0]
        last = (now - timedelta(days=random.randint(0, 20))).strftime("%Y-%m-%dT%H:%M:%S")
        cur.execute("INSERT OR REPLACE INTO soft_bounce_counter VALUES (?,?,?)",
                    (email, fails, last))

    cur.execute("DELETE FROM rule_suggestions")
    demo_suggestions = [
        ("no longer with our company", "hard_bounce", 0.92, "alice@former-corp.fr",
         "I am no longer with our company. Please update your records.",
         "Indicateur typique de départ d'employé — adresse à supprimer"),
        ("retired and no longer", "hard_bounce", 0.90, "retired-employee@old-corp.eu",
         "I have retired and no longer use this email address.", "Retraite — supprimer définitivement"),
        ("please use my new email", "address_change", 0.88, "old@example.fr",
         "Please use my new email: new@example.fr from now on.",
         "Demande explicite de changement d'adresse"),
        ("temporary delivery failure", "soft_bounce", 0.85, "user@temp-fail.com",
         "The server reports a temporary delivery failure, please retry later.",
         "Échec temporaire générique"),
        ("greylisting in effect", "soft_bounce", 0.82, "user@greylist.fr",
         "Your message has been greylisted. Try again in 5 minutes.",
         "Greylisting détecté — réessayer"),
    ]
    for pat, cat, conf, email, text, reason in demo_suggestions:
        ts = (now - timedelta(hours=random.randint(1, 48))).strftime("%Y-%m-%dT%H:%M:%S")
        cur.execute("""INSERT INTO rule_suggestions
               (pattern, category, confidence, sample_email, sample_text,
                llm_reason, suggested_at, status)
               VALUES (?,?,?,?,?,?,?, 'pending')""",
            (pat, cat, conf, email, text, reason, ts))
    conn.commit()
    conn.close()


def run_command_live(args: list) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            [sys.executable, "main.py"] + args,
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)
        return proc.returncode, (proc.stdout + proc.stderr)
    except subprocess.TimeoutExpired:
        return -1, "Timeout (>120s)"
    except Exception as e:
        return -1, str(e)


def plotly_dark(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Inter, sans-serif", size=12),
        title_font=dict(color="#f1f5f9", size=15),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.05)",
                   tickfont=dict(color="#94a3b8")),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.05)",
                   tickfont=dict(color="#94a3b8")),
        hoverlabel=dict(bgcolor="#1e293b", bordercolor="rgba(255,255,255,0.1)",
                        font=dict(color="#f1f5f9", family="Inter")),
    )
    return fig


def compute_health_score(result_df, soft_df, today_stats=None) -> int:
    if today_stats is not None:
        total = int(today_stats.get("total_processed", 0) or 0)
        if total == 0:
            return 95
        hard_pct = (today_stats.get("n_hard_bounce", 0) or 0) / total
        unknown_pct = (today_stats.get("n_unknown", 0) or 0) / total
    elif not result_df.empty:
        total = len(result_df)
        hard_pct = (result_df["category"] == "hard_bounce").sum() / total
        unknown_pct = (result_df["category"] == "unknown").sum() / total
    else:
        return 95
    critique = (soft_df["failures"] >= 5).sum() if not soft_df.empty else 0
    score = 100 - int(hard_pct * 40) - int(unknown_pct * 20) - min(int(critique) * 2, 20)
    return max(min(score, 100), 0)


def generate_insights(result_df, soft_df, stats_df, today_stats=None) -> list[dict]:
    insights = []
    if today_stats is not None and result_df.empty:
        total = int(today_stats.get("total_processed", 0) or 0)
        hard = int(today_stats.get("n_hard_bounce", 0) or 0)
        soft = int(today_stats.get("n_soft_bounce", 0) or 0)
        change = int(today_stats.get("n_address_change", 0) or 0)
        rules_pct = (int(today_stats.get("n_by_rules", 0) or 0) / total) if total else 0
    elif result_df.empty:
        return [{"type": "info", "text": "<span class='mi mi-sm'>lightbulb</span>&nbsp;&nbsp;Aucune activité aujourd'hui — système en attente du prochain poll."}]
    else:
        total = len(result_df)
        hard = (result_df["category"] == "hard_bounce").sum()
        soft = (result_df["category"] == "soft_bounce").sum()
        change = (result_df["category"] == "address_change").sum()
        rules_pct = (result_df["method"] == "rules").sum() / total

    if rules_pct > 0.85:
        insights.append({"type": "good", "text": f"<span class='mi mi-sm mi-green'>check_circle</span>&nbsp;&nbsp;<b>{rules_pct:.0%}</b> des bounces classifiés par les règles — économies sur les LLM."})
    if total and hard / total > 0.6:
        insights.append({"type": "warn", "text": f"<span class='mi mi-sm mi-amber'>warning</span>&nbsp;&nbsp;<b>{hard}</b> hard bounces ({hard/total:.0%}) — qualité de la base à surveiller."})
    if change > 0:
        insights.append({"type": "info", "text": f"<span class='mi mi-sm'>swap_horiz</span>&nbsp;&nbsp;<b>{change}</b> changement(s) d'adresse détecté(s) — à propager au CRM."})
    if not soft_df.empty:
        critique = (soft_df["failures"] >= 5).sum()
        if critique > 0:
            insights.append({"type": "warn", "text": f"<span class='mi mi-sm mi-red'>error</span>&nbsp;&nbsp;<b>{critique}</b> adresse(s) au-dessus du seuil de 5 soft bounces — pause auto."})
    if not result_df.empty:
        top_domain = result_df["email_address"].str.extract(r"@(.+)$")[0].value_counts()
        if len(top_domain) > 0 and top_domain.iloc[0] >= 5:
            insights.append({"type": "info", "text": f"<span class='mi mi-sm'>language</span>&nbsp;&nbsp;Domaine <b>{top_domain.index[0]}</b> concentre <b>{top_domain.iloc[0]}</b> bounces."})
        avg_conf = result_df["confidence"].mean()
        if avg_conf >= 0.90:
            insights.append({"type": "good", "text": f"<span class='mi mi-sm mi-green'>verified</span>&nbsp;&nbsp;Confiance moyenne <b>{avg_conf:.0%}</b> — décisions très fiables."})
    return insights or [{"type": "good", "text": "<span class='mi mi-sm mi-green'>check_circle</span>&nbsp;&nbsp;Aucune anomalie détectée."}]


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    # Logo (PNG si présent, sinon SVG fallback)
    st.markdown("<div class='logo-wrap'>", unsafe_allow_html=True)
    if LOGO_PNG.exists():
        st.image(str(LOGO_PNG), use_container_width=True)
    elif LOGO_SVG.exists():
        svg = LOGO_SVG.read_text(encoding="utf-8")
        b64 = base64.b64encode(svg.encode()).decode()
        st.markdown(
            f"<img src='data:image/svg+xml;base64,{b64}' style='width:100%; max-width:200px;'/>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-size:1.6rem; font-weight:800; color:#fafafa; letter-spacing:-0.02em;'>"
            "Cogi<span style='color:#3b82f6'>terra</span></div>"
            "<div style='font-size:0.7rem; letter-spacing:0.3em; color:#71717a; margin-top:4px;'>ÉDITIONS</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<div style='margin-top:0.8rem; font-size:0.78rem; color:#a1a1aa;'>"
        "Bounces Operations Center</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='margin-top:0.4rem;'><span class='pulse-dot'></span>"
        "<span style='color:#34d399; font-size:0.75rem; font-weight:600; "
        "margin-left:0.4rem; vertical-align:middle;'>SYSTÈME ACTIF</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Section : Actions
    st.markdown(
        "<div style='font-size:0.7rem; color:#71717a; letter-spacing:0.15em; "
        "font-weight:600; text-transform:uppercase; margin:1.2rem 0 0.6rem 0;'>"
        "<span class='mi mi-sm'>bolt</span>&nbsp;&nbsp;Actions Live</div>",
        unsafe_allow_html=True,
    )

    if st.button(":material/cloud_download: Poll IMAP", use_container_width=True, key="poll_btn"):
        with st.spinner("Connexion à Gandi IMAP..."):
            code, output = run_command_live(["--mode", "poll"])
        if code == 0:
            st.success("Poll terminé")
            st.cache_data.clear()
        else:
            st.error(f"Erreur (code {code})")
        with st.expander("Logs"):
            st.code(output[-2000:] if output else "(vide)", language="text")

    if st.button(":material/outgoing_mail: Générer rapport", use_container_width=True, key="report_btn"):
        with st.spinner("Génération + envoi..."):
            code, output = run_command_live(["--mode", "report"])
        if code == 0:
            st.success("Rapport envoyé")
            st.cache_data.clear()
        else:
            st.error(f"Erreur (code {code})")
        with st.expander("Logs"):
            st.code(output[-2000:] if output else "(vide)", language="text")

    # Section : Démo
    st.markdown(
        "<div style='font-size:0.7rem; color:#71717a; letter-spacing:0.15em; "
        "font-weight:600; text-transform:uppercase; margin:1.4rem 0 0.6rem 0;'>"
        "<span class='mi mi-sm'>auto_awesome</span>&nbsp;&nbsp;Mode Démo</div>",
        unsafe_allow_html=True,
    )
    if st.button(":material/auto_awesome: Injecter données démo", use_container_width=True, key="demo_btn"):
        inject_demo_data()
        st.cache_data.clear()
        st.success("60 bounces · 30j historique")
        time.sleep(0.4)
        st.rerun()

    # Section : Settings
    st.markdown(
        "<div style='font-size:0.7rem; color:#71717a; letter-spacing:0.15em; "
        "font-weight:600; text-transform:uppercase; margin:1.4rem 0 0.6rem 0;'>"
        "<span class='mi mi-sm'>tune</span>&nbsp;&nbsp;Paramètres</div>",
        unsafe_allow_html=True,
    )
    auto_refresh = st.toggle("Auto-refresh (5s)", value=False)
    if st.button(":material/refresh: Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Section : System
    st.markdown(
        "<div style='font-size:0.7rem; color:#71717a; letter-spacing:0.15em; "
        "font-weight:600; text-transform:uppercase; margin:1.4rem 0 0.6rem 0;'>"
        "<span class='mi mi-sm'>memory</span>&nbsp;&nbsp;Système</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:0.78rem; color:#a1a1aa; line-height:1.7;'>"
        "<b style='color:#cbd5e1'>Source</b> · Gandi IMAP<br/>"
        "<b style='color:#cbd5e1'>Stockage</b> · SQLite<br/>"
        "<b style='color:#cbd5e1'>Classifier</b> · Hybride règles + Claude<br/>"
        "<b style='color:#cbd5e1'>Seuil pause</b> · 5 soft bounces"
        "</div>", unsafe_allow_html=True,
    )
    if DB_PATH.exists():
        size = DB_PATH.stat().st_size / 1024
        st.caption(f"DB · {size:.1f} KB · {datetime.fromtimestamp(DB_PATH.stat().st_mtime).strftime('%H:%M:%S')}")


# =============================================================================
# HEADER (hero)
# =============================================================================
col_t, col_s = st.columns([3, 1])
with col_t:
    st.markdown(
        "<h1 style='display:flex; align-items:center; gap:0.7rem;'>"
        "<span class='mi mi-xl' style='color:#60a5fa;'>markunread_mailbox</span>"
        "Operations Center</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#a1a1aa; font-size:1.02rem; margin-top:-0.5rem;'>"
        "Pipeline temps réel · Bounces &amp; deliverability intelligence"
        "</p>", unsafe_allow_html=True,
    )
with col_s:
    st.markdown(
        f"<div style='text-align:right; padding-top:1.2rem;'>"
        f"<div class='badge badge-ok' style='font-size:0.7rem;'>"
        f"<span class='pulse-dot'></span>&nbsp;&nbsp;LIVE</div>"
        f"<div style='color:#71717a; font-size:0.75rem; margin-top:0.5rem; "
        f"font-variant-numeric:tabular-nums; letter-spacing:0.02em;'>"
        f"{datetime.now().strftime('%d %b %Y · %H:%M:%S')}</div>"
        f"</div>", unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

data = load_data()
result_df = data["result"]
stats_df = data["stats"]
soft_df = data["soft_counter"]

# Empty state
if result_df.empty and stats_df.empty:
    st.markdown(
        "<div class='bento' style='text-align:center; padding:4rem 2rem; "
        "background:linear-gradient(135deg, rgba(59,130,246,0.05), rgba(139,92,246,0.05));'>"
        "<div style='margin-bottom:1rem;'>"
        "<span class='mi mi-xl' style='font-size:4rem; color:#60a5fa;'>rocket_launch</span></div>"
        "<h2 style='color:#fafafa; margin:0 0 0.6rem 0;'>Démarrons l'expérience</h2>"
        "<p style='color:#94a3b8; font-size:1rem; max-width:600px; margin:0 auto 2rem;'>"
        "La base est vide. Lance un poll IMAP pour traiter les bounces de Gandi, "
        "ou utilise le mode démo pour explorer le dashboard avec des données réalistes."
        "</p>"
        "<p style='color:#71717a; font-size:0.85rem; margin:0;'>"
        "<span class='mi mi-sm'>arrow_forward</span> <b style='color:#cbd5e1'>Sidebar</b> · clique sur "
        "<b style='color:#60a5fa'>Injecter données démo</b> ou "
        "<b style='color:#60a5fa'>Poll IMAP</b>"
        "</p>"
        "</div>", unsafe_allow_html=True,
    )
    if auto_refresh:
        time.sleep(5)
        st.rerun()
    st.stop()


# =============================================================================
# KPI LOGIC (fallback to stats if result vidée)
# =============================================================================
today_str = datetime.now().strftime("%Y-%m-%d")
today_stats = None
if not stats_df.empty:
    rows = stats_df[stats_df["report_date"].astype(str).str.startswith(today_str)]
    if not rows.empty:
        today_stats = rows.iloc[0]

if not result_df.empty:
    total_today = len(result_df)
    hard = int((result_df["category"] == "hard_bounce").sum())
    soft = int((result_df["category"] == "soft_bounce").sum())
    change = int((result_df["category"] == "address_change").sum())
    KPI_FROM_STATS = False
elif today_stats is not None:
    total_today = int(today_stats.get("total_processed", 0) or 0)
    hard = int(today_stats.get("n_hard_bounce", 0) or 0)
    soft = int(today_stats.get("n_soft_bounce", 0) or 0)
    change = int(today_stats.get("n_address_change", 0) or 0)
    KPI_FROM_STATS = True
else:
    total_today = hard = soft = change = 0
    KPI_FROM_STATS = False

surveillance = len(soft_df)
in_alert = int((soft_df["failures"] >= 3).sum()) if not soft_df.empty else 0
critique = int((soft_df["failures"] >= 5).sum()) if not soft_df.empty else 0
total_all = int(stats_df["total_processed"].sum()) if not stats_df.empty else 0
if not result_df.empty:
    total_all += total_today
saved_eur = (total_all * COST_PER_EMAIL_CENTS) / 100
health = compute_health_score(result_df, soft_df, today_stats)


# =============================================================================
# BENTO GRID HERO
# =============================================================================
# Ligne 1 : 6 KPIs
k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1: st.metric(":material/inbox: Aujourd'hui", total_today)
with k2: st.metric(":material/error: Hard", hard)
with k3: st.metric(":material/schedule: Soft", soft)
with k4: st.metric(":material/swap_horiz: Changements", change)
with k5: st.metric(":material/visibility: Surveillance", surveillance, f"{critique} crit." if critique else None)
with k6: st.metric(":material/savings: Économies", f"{saved_eur:.2f} €", f"{total_all} évités")

if KPI_FROM_STATS:
    st.markdown(
        "<div class='insight insight-good' style='margin-top:0.8rem'>"
        "<span class='mi mi-sm'>insights</span>&nbsp;&nbsp;"
        "Données consolidées depuis le rapport quotidien (table <code>result</code> vidée). "
        "Lance un nouveau poll pour traiter d'autres emails."
        "</div>", unsafe_allow_html=True,
    )

st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)


# =============================================================================
# Ligne 2 : Bento Health + Insights
# =============================================================================
col_health, col_insights = st.columns([2, 3])

with col_health:
    st.markdown(
        "<div class='bento'>"
        "<h4><span class='mi mi-sm'>health_and_safety</span>&nbsp;&nbsp;Health Score</h4>",
        unsafe_allow_html=True,
    )
    score_color = "#10b981" if health >= 80 else ("#f59e0b" if health >= 60 else "#ef4444")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health,
        domain={"x": [0, 1], "y": [0, 1]},
        number={"font": {"size": 64, "color": "#fafafa", "family": "Inter"},
                "suffix": "<span style='font-size:18px;color:#71717a'> / 100</span>"},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0,
                     "tickfont": {"color": "#71717a", "size": 10}, "showticklabels": False},
            "bar": {"color": score_color, "thickness": 0.85, "line": {"color": score_color, "width": 0}},
            "bgcolor": "rgba(255,255,255,0.04)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 60], "color": "rgba(239,68,68,0.08)"},
                {"range": [60, 80], "color": "rgba(245,158,11,0.08)"},
                {"range": [80, 100], "color": "rgba(16,185,129,0.08)"},
            ],
        },
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=15, b=15),
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    status_label = "Excellent" if health >= 80 else ("À surveiller" if health >= 60 else "Critique")
    badge_class = "badge-ok" if health >= 80 else ("badge-warn" if health >= 60 else "badge-danger")
    st.markdown(
        f"<div style='text-align:center; margin-top:-1rem;'>"
        f"<span class='badge {badge_class}'>{status_label}</span></div>"
        f"</div>", unsafe_allow_html=True,
    )

with col_insights:
    st.markdown("<div class='bento'>"
                "<h4><span class='mi mi-sm'>psychology</span>&nbsp;&nbsp;Insights automatiques</h4>",
                unsafe_allow_html=True)
    for ins in generate_insights(result_df, soft_df, stats_df, today_stats):
        css = {"good": "insight insight-good", "warn": "insight insight-warn",
               "info": "insight"}.get(ins["type"], "insight")
        st.markdown(f"<div class='{css}'>{ins['text']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)


# =============================================================================
# TABS
# =============================================================================
tab_overview, tab_today, tab_surv, tab_hist, tab_live, tab_rules, tab_data = st.tabs([
    ":material/dashboard: Vue d'ensemble",
    ":material/today: Aujourd'hui",
    ":material/visibility: Surveillance",
    ":material/trending_up: Historique 30j",
    ":material/bolt: Activité live",
    ":material/smart_toy: Règles suggérées",
    ":material/database: Données",
])

# Pour les graphiques : fallback sur stats si result vide
if not result_df.empty:
    cat_data = result_df["category"].value_counts().to_dict()
    method_data = result_df["method"].value_counts().to_dict()
    total_for_pie = len(result_df)
elif today_stats is not None:
    cat_data = {
        "hard_bounce":     int(today_stats.get("n_hard_bounce", 0) or 0),
        "soft_bounce":     int(today_stats.get("n_soft_bounce", 0) or 0),
        "address_change":  int(today_stats.get("n_address_change", 0) or 0),
        "technical_error": int(today_stats.get("n_technical", 0) or 0),
        "unknown":         int(today_stats.get("n_unknown", 0) or 0),
    }
    cat_data = {k: v for k, v in cat_data.items() if v > 0}
    method_data = {
        "rules": int(today_stats.get("n_by_rules", 0) or 0),
        "llm":   int(today_stats.get("n_by_llm", 0) or 0),
    }
    total_for_pie = int(today_stats.get("total_processed", 0) or 0)
else:
    cat_data = method_data = {}
    total_for_pie = 0


# --------------------------------------------------- VUE D'ENSEMBLE
with tab_overview:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='bento'>"
                    "<h4><span class='mi mi-sm'>donut_large</span>&nbsp;&nbsp;Distribution par catégorie</h4>",
                    unsafe_allow_html=True)
        if cat_data:
            labels = [CATEGORY_LABELS.get(k, k) for k in cat_data.keys()]
            values = list(cat_data.values())
            colors = [CATEGORY_COLORS.get(k, "#64748b") for k in cat_data.keys()]
            fig = go.Figure(data=[go.Pie(
                labels=labels, values=values, hole=0.7,
                marker=dict(colors=colors, line=dict(color="#07080F", width=3)),
                textfont=dict(size=12, color="white", family="Inter"),
                textposition="outside", textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>%{value} bounces<br>%{percent}<extra></extra>",
            )])
            fig.update_layout(
                showlegend=False, height=350,
                annotations=[dict(
                    text=f"<b style='font-size:34px;color:#fafafa'>{total_for_pie}</b><br>"
                         f"<span style='font-size:11px;color:#71717a;letter-spacing:0.08em'>BOUNCES</span>",
                    x=0.5, y=0.5, showarrow=False)])
            st.plotly_chart(plotly_dark(fig), use_container_width=True)
        else:
            st.info("Pas de données.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='bento'>"
                    "<h4><span class='mi mi-sm'>settings</span>&nbsp;&nbsp;Règles "
                    "vs <span class='mi mi-sm mi-violet'>smart_toy</span>&nbsp;&nbsp;LLM</h4>",
                    unsafe_allow_html=True)
        if method_data and sum(method_data.values()) > 0:
            labels = ["⚙️ Règles déterministes", "🤖 LLM Claude Haiku"]
            values = [method_data.get("rules", 0), method_data.get("llm", 0)]
            fig = go.Figure(data=[go.Pie(
                labels=labels, values=values, hole=0.7,
                marker=dict(colors=["#3b82f6", "#a855f7"], line=dict(color="#07080F", width=3)),
                textfont=dict(color="white", size=12, family="Inter"),
                hovertemplate="<b>%{label}</b><br>%{value}<br>%{percent}<extra></extra>",
            )])
            tot = sum(values)
            rule_pct = values[0] / tot * 100 if tot else 0
            fig.update_layout(
                showlegend=False, height=350,
                annotations=[dict(
                    text=f"<b style='font-size:30px;color:#fafafa'>{rule_pct:.0f}%</b><br>"
                         f"<span style='font-size:11px;color:#71717a;letter-spacing:0.08em'>RÈGLES</span>",
                    x=0.5, y=0.5, showarrow=False)])
            st.plotly_chart(plotly_dark(fig), use_container_width=True)
        else:
            st.info("Pas de données.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='bento'>"
                "<h4><span class='mi mi-sm'>language</span>&nbsp;&nbsp;Top 10 domaines en échec</h4>",
                unsafe_allow_html=True)
    if not result_df.empty:
        result_df["domain"] = result_df["email_address"].str.extract(r"@(.+)$")
        top = result_df["domain"].value_counts().head(10).reset_index()
        top.columns = ["domain", "count"]
        fig = px.bar(top, x="count", y="domain", orientation="h", text="count",
                     color="count", color_continuous_scale=[[0, "#3b82f6"], [1, "#ef4444"]])
        fig.update_traces(textfont_color="#fafafa", textposition="outside",
                          marker=dict(line=dict(width=0)))
        fig.update_layout(height=380, showlegend=False, coloraxis_showscale=False,
                          yaxis=dict(autorange="reversed", title=""),
                          xaxis_title="Bounces")
        st.plotly_chart(plotly_dark(fig), use_container_width=True)
    else:
        st.info("Pas de données aujourd'hui.")
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------- AUJOURD'HUI
with tab_today:
    st.markdown(f"<div class='bento'>"
                f"<h4><span class='mi mi-sm'>today</span>&nbsp;&nbsp;"
                f"Activité du {datetime.now().strftime('%d %B %Y')}</h4>",
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        cat_filter = st.multiselect("Catégorie", list(CATEGORY_LABELS.values()),
                                     default=list(CATEGORY_LABELS.values()))
    with c2:
        method_filter = st.multiselect("Méthode", ["rules", "llm"], default=["rules", "llm"])
    with c3:
        search = st.text_input("🔍 Recherche", placeholder="email ou domaine...")

    filtered = result_df.copy()
    cat_keys = [k for k, v in CATEGORY_LABELS.items() if v in cat_filter]
    if cat_keys:
        filtered = filtered[filtered["category"].isin(cat_keys)]
    if method_filter:
        filtered = filtered[filtered["method"].isin(method_filter)]
    if search:
        filtered = filtered[filtered["email_address"].str.contains(search, case=False, na=False)]

    st.markdown(
        f"<div style='margin:0.5rem 0; color:#94a3b8; font-size:0.85rem;'>"
        f"<b style='color:#fafafa'>{len(filtered)}</b> résultat(s)</div>",
        unsafe_allow_html=True,
    )

    if not filtered.empty:
        disp = filtered.copy()
        disp["category"] = disp["category"].map(CATEGORY_LABELS)
        disp["confidence"] = disp["confidence"].apply(lambda x: f"{x:.0%}")
        cols = ["email_address", "category", "confidence", "method", "reason", "new_email", "processed_at"]
        cols = [c for c in cols if c in disp.columns]
        st.dataframe(disp[cols], use_container_width=True, hide_index=True, height=480)
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(":material/download: Exporter CSV", csv,
                           file_name=f"bounces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                           mime="text/csv")
    else:
        st.info("Aucun résultat pour ces filtres.")
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------- SURVEILLANCE
with tab_surv:
    st.markdown(
        "<div class='bento'>"
        "<h4><span class='mi mi-sm'>visibility</span>&nbsp;&nbsp;"
        "Surveillance soft bounces (cumul cross-jours)</h4>"
        "<p style='color:#71717a; font-size:0.82rem; margin-top:-0.3rem;'>"
        "Adresses dont les soft bounces s'accumulent. À partir de 5 → mise en pause auto.</p>",
        unsafe_allow_html=True,
    )

    if soft_df.empty:
        st.info("Aucune adresse sous surveillance.")
    else:
        col_chart, col_stat = st.columns([3, 2])
        with col_chart:
            dist = soft_df["failures"].value_counts().sort_index().reset_index()
            dist.columns = ["failures", "count"]
            dist["zone"] = dist["failures"].apply(
                lambda x: "🔴 Critique" if x >= 5 else ("🟠 Alerte" if x >= 3 else "🟢 OK"))
            fig = px.bar(dist, x="failures", y="count", color="zone", text="count",
                         color_discrete_map={"🟢 OK": "#10b981", "🟠 Alerte": "#f59e0b", "🔴 Critique": "#ef4444"})
            fig.update_traces(textposition="outside", textfont_color="#fafafa",
                              marker=dict(line=dict(width=0)))
            fig.update_layout(height=340, xaxis_title="Échecs cumulés",
                              yaxis_title="Adresses", legend_title_text="")
            st.plotly_chart(plotly_dark(fig), use_container_width=True)

        with col_stat:
            ok = (soft_df["failures"] < 3).sum()
            alerte = ((soft_df["failures"] >= 3) & (soft_df["failures"] < 5)).sum()
            critique_n = (soft_df["failures"] >= 5).sum()
            for label, n, color, sub, icon in [
                ("Sereines", ok, "#10b981", "< 3 échecs", "check_circle"),
                ("Alerte", alerte, "#f59e0b", "3 à 4 échecs", "warning"),
                ("Critiques", critique_n, "#ef4444", "≥ 5 → pause auto", "error"),
            ]:
                st.markdown(
                    f"<div class='bento bento-tight' style='margin-bottom:0.5rem;'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                    f"<div><div style='color:#71717a; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.1em;'>{label}</div>"
                    f"<div style='font-size:1.8rem; font-weight:800; color:{color}; line-height:1.1;'>{n}</div>"
                    f"<div style='color:#71717a; font-size:0.75rem;'>{sub}</div></div>"
                    f"<div><span class='mi mi-xl mi-fill' style='color:{color};'>{icon}</span></div>"
                    f"</div></div>", unsafe_allow_html=True,
                )

        st.markdown(
            "<h4 style='margin-top:1rem'>"
            "<span class='mi mi-sm'>list</span>&nbsp;&nbsp;Adresses surveillées</h4>",
            unsafe_allow_html=True,
        )
        soft_disp = soft_df.copy()
        soft_disp["•"] = soft_disp["failures"].apply(
            lambda x: "🔴" if x >= 5 else ("🟠" if x >= 3 else "🟢"))
        cols_display = ["•", "email_address", "failures", "last_failure"]
        soft_disp = soft_disp[cols_display].rename(columns={
            "email_address": "Email", "failures": "Échecs", "last_failure": "Dernier",
        })
        st.dataframe(soft_disp, use_container_width=True, hide_index=True, height=320)
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------- HISTORIQUE
with tab_hist:
    st.markdown("<div class='bento'>"
                "<h4><span class='mi mi-sm'>trending_up</span>&nbsp;&nbsp;Évolution sur 30 jours</h4>",
                unsafe_allow_html=True)
    if stats_df.empty:
        st.info("Pas d'historique. Utilise le mode démo ou lance plusieurs rapports.")
    else:
        stats_df["report_date"] = pd.to_datetime(stats_df["report_date"])
        recent = stats_df.head(30).sort_values("report_date")
        fig = go.Figure()
        SERIES = [
            ("n_hard_bounce", "Hard", "#ef4444", "rgba(239,68,68,0.30)"),
            ("n_soft_bounce", "Soft", "#f59e0b", "rgba(245,158,11,0.30)"),
            ("n_address_change", "Changement", "#3b82f6", "rgba(59,130,246,0.30)"),
            ("n_unknown", "Unknown", "#64748b", "rgba(100,116,139,0.30)"),
        ]
        for col, name, line_color, fill_color in SERIES:
            if col in recent.columns:
                fig.add_trace(go.Scatter(
                    x=recent["report_date"], y=recent[col], mode="lines+markers",
                    name=name, stackgroup="one",
                    line=dict(color=line_color, width=2.5),
                    marker=dict(size=5, line=dict(color="#07080F", width=1)),
                    fillcolor=fill_color,
                ))
        fig.update_layout(height=400, hovermode="x unified",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                      xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(plotly_dark(fig), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='bento'>"
                        "<h4><span class='mi mi-sm mi-violet'>smart_toy</span>&nbsp;&nbsp;"
                        "Performance du classifier</h4>", unsafe_allow_html=True)
            fig = go.Figure(data=[
                go.Bar(name="⚙️ Règles", x=recent["report_date"], y=recent["n_by_rules"],
                       marker_color="#3b82f6", marker_line_width=0),
                go.Bar(name="🤖 LLM", x=recent["report_date"], y=recent["n_by_llm"],
                       marker_color="#a855f7", marker_line_width=0),
            ])
            fig.update_layout(barmode="stack", height=320,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                          bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(plotly_dark(fig), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='bento'>"
                        "<h4><span class='mi mi-sm mi-green'>verified</span>&nbsp;&nbsp;Confiance moyenne</h4>",
                        unsafe_allow_html=True)
            if "avg_confidence" in recent.columns:
                fig = px.line(recent, x="report_date", y="avg_confidence", markers=True)
                fig.update_traces(line=dict(color="#10b981", width=2.5),
                                  marker=dict(size=6, color="#10b981",
                                              line=dict(color="#07080F", width=1)))
                fig.update_layout(height=320,
                                  yaxis=dict(range=[0.7, 1], tickformat=".0%", title="Confiance"))
                fig.add_hline(y=0.85, line_dash="dash", line_color="#71717a",
                              annotation_text="Seuil 85%",
                              annotation_position="right",
                              annotation_font_color="#94a3b8")
                st.plotly_chart(plotly_dark(fig), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------- LIVE
with tab_live:
    st.markdown("<div class='bento'>"
                "<h4><span class='mi mi-sm'>bolt</span>&nbsp;&nbsp;Flux d'activité temps réel</h4>",
                unsafe_allow_html=True)
    if result_df.empty:
        st.info("Aucune activité récente.")
    else:
        st.caption(f"Les {min(20, len(result_df))} derniers événements")
        st.markdown("<div style='margin-top:0.8rem;'>", unsafe_allow_html=True)
        for _, row in result_df.head(20).iterrows():
            cat = row["category"]
            color = CATEGORY_COLORS.get(cat, "#64748b")
            label = CATEGORY_LABELS.get(cat, cat)
            method_icon = ("<span class='mi mi-sm'>settings</span>" if row.get("method") == "rules"
                           else "<span class='mi mi-sm mi-violet'>smart_toy</span>")
            conf_pct = f"{row.get('confidence', 0):.0%}" if pd.notna(row.get("confidence")) else "—"
            ts = str(row.get("processed_at", ""))[-8:]
            st.markdown(
                f"<div class='feed-card'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                f"<div style='flex:1;'>"
                f"<span style='background:{color}; color:white; padding:2px 9px; border-radius:5px;"
                f"font-size:0.65rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase;'>{label}</span>"
                f" <b style='color:#fafafa; margin-left:0.4rem;'>{row['email_address']}</b><br/>"
                f"<small style='color:#71717a;'>{row.get('reason', '')}</small>"
                f"</div>"
                f"<div style='text-align:right; min-width:90px;'>"
                f"<span style='color:#cbd5e1; font-size:0.82rem; font-weight:500;'>{method_icon} {conf_pct}</span><br/>"
                f"<small style='color:#52525b; font-variant-numeric:tabular-nums;'>{ts}</small>"
                f"</div></div></div>", unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------- RULES
with tab_rules:
    st.markdown(
        "<div class='bento'>"
        "<h4><span class='mi mi-sm mi-violet'>smart_toy</span>&nbsp;&nbsp;Système auto-apprenant</h4>"
        "<p style='color:#71717a; font-size:0.85rem;'>"
        "Quand le LLM est sollicité, il propose une regex qui pourrait éviter de l'appeler la prochaine fois. "
        "Adopte les bonnes en un clic pour réduire les coûts API et accélérer le pipeline."
        "</p>", unsafe_allow_html=True,
    )

    sug_df = data["suggestions"]
    user_rules = load_user_rules()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(":material/hourglass_empty: En attente",
                  int((sug_df["status"] == "pending").sum()) if not sug_df.empty else 0)
    with c2:
        st.metric(":material/check_circle: Adoptées",
                  int((sug_df["status"] == "adopted").sum()) if not sug_df.empty else 0)
    with c3:
        st.metric(":material/library_books: Règles actives", len(user_rules))

    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)

    f_status = st.radio("Filtrer par statut", ["pending", "adopted", "rejected", "all"],
                       horizontal=True, index=0, label_visibility="collapsed")
    if not sug_df.empty:
        filtered_sug = sug_df if f_status == "all" else sug_df[sug_df["status"] == f_status]
    else:
        filtered_sug = pd.DataFrame()

    if filtered_sug.empty:
        st.info(
            "Aucune suggestion pour ce filtre. Configure `LLM_API_KEY` dans `.env` "
            "puis lance `--mode poll`. Sinon, utilise le **Mode démo** dans la sidebar."
        )
    else:
        for _, row in filtered_sug.iterrows():
            sug_id = int(row["id"])
            pattern = row["pattern"]
            cat = row["category"]
            conf = float(row["confidence"])
            status = row["status"]
            color = CATEGORY_COLORS.get(cat, "#64748b")
            label = CATEGORY_LABELS.get(cat, cat)
            status_badge = ("badge-ok" if status == "adopted"
                            else ("badge-warn" if status == "pending" else "badge-danger"))
            st.markdown(
                f"<div class='bento bento-tight' style='margin-bottom:0.7rem;'>"
                f"<div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.6rem;'>"
                f"<div>"
                f"<span style='background:{color}; color:white; padding:3px 10px; border-radius:5px; "
                f"font-size:0.65rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase;'>{label}</span>"
                f" <span class='badge badge-info'>{conf:.0%}</span>"
                f" <span class='badge {status_badge}'>{status}</span>"
                f"</div>"
                f"<small style='color:#52525b; font-variant-numeric:tabular-nums;'>#{sug_id} · {row['suggested_at'][:16]}</small>"
                f"</div>"
                f"<div style='background:rgba(0,0,0,0.4); padding:0.7rem 1rem; border-radius:10px; "
                f"font-family:JetBrains Mono, monospace; color:#86efac; margin-bottom:0.6rem; "
                f"word-break:break-all; border:1px solid rgba(255,255,255,0.06);'>"
                f"/{pattern}/i</div>"
                f"<div style='color:#a1a1aa; font-size:0.82rem; margin-bottom:0.25rem;'>"
                f"<span class='mi mi-sm'>lightbulb</span>&nbsp;&nbsp;<i>{row.get('llm_reason', '')}</i></div>"
                f"<div style='color:#71717a; font-size:0.78rem;'>"
                f"<span class='mi mi-sm'>email</span>&nbsp;&nbsp;<code>{row.get('sample_email', '')}</code></div>"
                f"<div style='color:#52525b; font-size:0.78rem; margin-top:0.2rem;'>"
                f"<span class='mi mi-sm'>description</span>&nbsp;&nbsp;<i>{(row.get('sample_text') or '')[:180]}…</i></div>"
                f"</div>", unsafe_allow_html=True,
            )
            if status == "pending":
                bc1, bc2, _ = st.columns([1, 1, 4])
                with bc1:
                    if st.button(":material/check_circle: Adopter", key=f"adopt_{sug_id}",
                                 use_container_width=True):
                        if adopt_suggestion(sug_id, pattern, cat, conf, row.get("llm_reason", "")):
                            st.success("Adoptée et ajoutée à user_rules.json")
                            st.cache_data.clear()
                            time.sleep(0.4)
                            st.rerun()
                        else:
                            st.error("Regex invalide")
                with bc2:
                    if st.button(":material/close: Rejeter", key=f"reject_{sug_id}",
                                 use_container_width=True):
                        reject_suggestion(sug_id)
                        st.cache_data.clear()
                        time.sleep(0.3)
                        st.rerun()

    if user_rules:
        st.markdown(
            "<h4 style='margin-top:1.5rem'>"
            "<span class='mi mi-sm'>library_books</span>&nbsp;&nbsp;Règles actives</h4>",
            unsafe_allow_html=True,
        )
        st.caption("Chargées depuis data/user_rules.json — priorité absolue sur les règles hardcodées.")
        df_rules = pd.DataFrame(user_rules)
        st.dataframe(df_rules, use_container_width=True, hide_index=True, height=240)
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------- DATA
with tab_data:
    st.markdown("<div class='bento'>"
                "<h4><span class='mi mi-sm'>database</span>&nbsp;&nbsp;Exploration SQLite</h4>",
                unsafe_allow_html=True)
    sub = st.radio("Table :",
                   ["result", "stats", "soft_bounce_counter", "counters", "rule_suggestions"],
                   horizontal=True)
    df_map = {"result": result_df, "stats": stats_df,
              "soft_bounce_counter": soft_df, "counters": data["counters"],
              "rule_suggestions": data["suggestions"]}
    df = df_map[sub]
    st.markdown(
        f"<div style='color:#94a3b8; font-size:0.85rem; margin:0.5rem 0;'>"
        f"<b style='color:#fafafa'>{len(df)}</b> ligne(s) · "
        f"<b style='color:#fafafa'>{len(df.columns)}</b> colonne(s)</div>",
        unsafe_allow_html=True,
    )
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True, height=480)
        st.download_button(":material/download: Exporter en CSV",
                           df.to_csv(index=False).encode("utf-8"),
                           file_name=f"{sub}_{datetime.now().strftime('%Y%m%d')}.csv",
                           mime="text/csv")
    else:
        st.info("Table vide.")
    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# AUTO-REFRESH
# =============================================================================
if auto_refresh:
    time.sleep(5)
    st.rerun()


# =============================================================================
# FOOTER
# =============================================================================
st.markdown(
    "<div style='text-align:center; color:#52525b; font-size:0.75rem; "
    "padding:1.5rem 0; margin-top:1rem; border-top:1px solid rgba(255,255,255,0.04);'>"
    "<b style='color:#a1a1aa;'>Cogiterra Bounces Operations</b> · "
    "Hackathon H3 Hitema 2026 · "
    "BAL surveillée <code>hackathon@cogiterra.fr</code> · "
    "<span style='color:#34d399'><span class='pulse-dot'></span>&nbsp;&nbsp;Système opérationnel</span>"
    "</div>", unsafe_allow_html=True,
)
