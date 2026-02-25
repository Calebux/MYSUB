"""
app.py — Streamlit Dashboard for Subscription Manager

Design system: Stripe-inspired
  Background:      #f6f9fc
  Surface:         #ffffff
  Border:          #e3e8ee
  Text primary:    #32325d
  Text secondary:  #525f7f
  Text muted:      #8898aa
  Accent:          #635bff
  Success:         #2dce89
  Warning:         #fb6340
  Danger:          #f5365c
  Shadow:          0 2px 5px rgba(50,50,93,.1), 0 1px 2px rgba(0,0,0,.06)
"""

import json
import threading
import time
import urllib.parse
from datetime import date
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="SubTrack — Subscription Manager",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Hide Streamlit chrome ── */
#MainMenu, header, footer { display: none !important; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #f6f9fc !important;
    color: #32325d;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
}
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 860px !important;
}

/* ── Header ── */
.st-header {
    margin-bottom: 2rem;
}
.app-logo {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.2rem;
}
.app-logo-icon {
    width: 36px; height: 36px;
    background: #635bff;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
    box-shadow: 0 4px 12px rgba(99,91,255,0.35);
}
.app-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #32325d;
    letter-spacing: -0.3px;
}
.app-subtitle {
    color: #8898aa;
    font-size: 0.88rem;
    margin-bottom: 2rem;
    margin-left: 0;
}

/* ── Step bar ── */
.step-bar {
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: 2.5rem;
    background: #ffffff;
    border: 1px solid #e3e8ee;
    border-radius: 12px;
    padding: 0.2rem;
    box-shadow: 0 1px 3px rgba(50,50,93,.06);
}
.step {
    flex: 1;
    text-align: center;
    padding: 0.55rem 0.5rem;
    border-radius: 9px;
    font-size: 0.78rem;
    font-weight: 500;
    color: #8898aa;
    transition: all 0.2s;
    cursor: default;
}
.step.active {
    background: #635bff;
    color: #ffffff;
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(99,91,255,0.4);
}
.step.done {
    color: #635bff;
    font-weight: 600;
}

/* ── Cards ── */
.card {
    background: #ffffff;
    border: 1px solid #e3e8ee;
    border-radius: 12px;
    padding: 1.75rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 2px 5px rgba(50,50,93,.07), 0 1px 2px rgba(0,0,0,.05);
}
.card-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #32325d;
    margin-bottom: 0.35rem;
}
.card-desc {
    color: #8898aa;
    font-size: 0.85rem;
    margin-bottom: 1.5rem;
    line-height: 1.5;
}

/* ── Stat grid ── */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.75rem;
}
@media (max-width: 600px) { .stat-grid { grid-template-columns: 1fr; } }
.stat-card {
    background: #ffffff;
    border: 1px solid #e3e8ee;
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 2px 5px rgba(50,50,93,.07), 0 1px 2px rgba(0,0,0,.04);
    border-top: 3px solid #635bff;
}
.stat-card.green  { border-top-color: #2dce89; }
.stat-card.orange { border-top-color: #fb6340; }
.stat-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #8898aa;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.5rem;
}
.stat-value {
    font-size: 1.55rem;
    font-weight: 700;
    color: #32325d;
    line-height: 1;
}
.stat-value.purple { color: #635bff; }
.stat-value.green  { color: #2dce89; }
.stat-value.orange { color: #fb6340; }
.stat-sub {
    font-size: 0.75rem;
    color: #8898aa;
    margin-top: 0.3rem;
}

/* ── Section headers ── */
.section-header {
    font-size: 0.72rem;
    font-weight: 700;
    color: #8898aa;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 2rem 0 0.85rem;
}

/* ── Subscription rows ── */
.sub-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.2rem;
    background: #ffffff;
    border: 1px solid #e3e8ee;
    border-radius: 10px;
    margin-bottom: 0.5rem;
    gap: 1rem;
    box-shadow: 0 1px 3px rgba(50,50,93,.05);
    transition: box-shadow 0.15s;
}
.sub-row:hover {
    box-shadow: 0 4px 12px rgba(50,50,93,.1), 0 1px 3px rgba(0,0,0,.06);
}
.sub-icon {
    width: 38px; height: 38px;
    background: #f6f9fc;
    border: 1px solid #e3e8ee;
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
}
.sub-merchant { font-weight: 600; font-size: 0.95rem; color: #32325d; }
.sub-category  { font-size: 0.72rem; color: #8898aa; margin-top: 2px; }
.sub-amount    { font-size: 1rem; font-weight: 700; color: #32325d; white-space: nowrap; }
.sub-freq      { font-size: 0.72rem; color: #8898aa; text-align: right; margin-top: 2px; }

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.badge-warning { background: rgba(251,99,64,.1);  color: #fb6340; }
.badge-danger  { background: rgba(245,54,92,.1);  color: #f5365c; }
.badge-success { background: rgba(45,206,137,.1); color: #2dce89; }
.badge-info    { background: rgba(99,91,255,.1);  color: #635bff; }

/* ── Overlap card ── */
.overlap-card {
    background: rgba(245,54,92,.04);
    border: 1px solid rgba(245,54,92,.2);
    border-left: 3px solid #f5365c;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.overlap-title { color: #f5365c; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.3rem; }
.overlap-desc  { color: #525f7f; font-size: 0.83rem; line-height: 1.5; }

/* ── Renewal pill ── */
.renewal-pill {
    display: inline-block;
    background: rgba(251,99,64,.1);
    color: #fb6340;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: 600;
}

/* ── Log box ── */
.log-box {
    background: #f6f9fc;
    border: 1px solid #e3e8ee;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.76rem;
    color: #525f7f;
    max-height: 240px;
    overflow-y: auto;
    line-height: 1.7;
}

/* ── Scan spinner ── */
@keyframes scan-spin { to { transform: rotate(360deg); } }
.scan-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2.5rem 0 1.5rem;
}
.scan-spinner {
    width: 48px; height: 48px;
    border: 3px solid #e3e8ee;
    border-top-color: #635bff;
    border-radius: 50%;
    animation: scan-spin 0.8s linear infinite;
    margin-bottom: 1rem;
}
.scan-label {
    color: #8898aa;
    font-size: 0.85rem;
    font-weight: 500;
}

/* ── Info cards (connect page) ── */
.info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.85rem;
    margin-top: 1rem;
}
.info-card {
    background: #ffffff;
    border: 1px solid #e3e8ee;
    border-radius: 10px;
    padding: 1rem 1.1rem;
    box-shadow: 0 1px 3px rgba(50,50,93,.05);
}
.info-icon { font-size: 1.25rem; margin-bottom: 0.4rem; }
.info-title { font-size: 0.85rem; font-weight: 600; color: #32325d; margin-bottom: 0.2rem; }
.info-desc  { font-size: 0.76rem; color: #8898aa; line-height: 1.4; }

/* ── Alert cards ── */
.alert-card {
    background: #ffffff;
    border: 1px solid #e3e8ee;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 3px rgba(50,50,93,.05);
}
.alert-card-title { font-size: 0.92rem; font-weight: 600; color: #32325d; }
.alert-card-desc  { font-size: 0.78rem; color: #8898aa; margin-top: 0.15rem; }
.alert-steps {
    background: #f6f9fc;
    border: 1px solid #e3e8ee;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    font-size: 0.78rem;
    color: #525f7f;
    line-height: 1.9;
    margin: 0.75rem 0;
}

/* ── Inputs ── */
.stTextInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid #e3e8ee !important;
    color: #32325d !important;
    border-radius: 8px !important;
    padding: 0.65rem 0.9rem !important;
    font-size: 0.9rem !important;
    box-shadow: 0 1px 3px rgba(50,50,93,.05) !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextInput > div > div > input:focus {
    border-color: #635bff !important;
    box-shadow: 0 0 0 3px rgba(99,91,255,.15) !important;
    outline: none !important;
}
.stTextInput > label { color: #525f7f !important; font-size: 0.82rem !important; font-weight: 500 !important; }

/* ── Buttons — primary (default) ── */
.stButton > button {
    background: #635bff !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.4rem !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    width: 100% !important;
    box-shadow: 0 4px 6px rgba(99,91,255,.25) !important;
    transition: all 0.15s !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    background: #5851ea !important;
    box-shadow: 0 7px 14px rgba(99,91,255,.3), 0 3px 6px rgba(0,0,0,.08) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Buttons — secondary (outline) ── */
[data-testid="stBaseButton-secondary"] {
    background: #ffffff !important;
    color: #635bff !important;
    border: 1.5px solid #635bff !important;
    box-shadow: none !important;
}
[data-testid="stBaseButton-secondary"]:hover {
    background: rgba(99,91,255,.06) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ── Nav row: close gap so buttons sit flush left / right ── */
.nav-row [data-testid="stHorizontalBlock"] {
    gap: 0.75rem !important;
}
.nav-row [data-testid="stColumn"]:first-child { padding-right: 0 !important; }
.nav-row [data-testid="stColumn"]:last-child  { padding-left:  0 !important; }

/* ── Progress bar ── */
.stProgress > div > div > div {
    background: #635bff !important;
    border-radius: 999px !important;
}
[data-testid="stProgressBar"] > div {
    background: #e3e8ee !important;
    border-radius: 999px !important;
}

/* ── Checkbox ── */
.stCheckbox > label { color: #525f7f !important; font-size: 0.85rem !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e3e8ee !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(50,50,93,.05) !important;
}
[data-testid="stExpander"] summary { color: #32325d !important; font-weight: 500 !important; }

/* ── Success / error / warning ── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── Divider ── */
hr { border-color: #e3e8ee !important; margin: 1.5rem 0 !important; }

/* ── Download button ── */
.stDownloadButton > button {
    background: #ffffff !important;
    color: #635bff !important;
    border: 1px solid #635bff !important;
    box-shadow: none !important;
}
.stDownloadButton > button:hover {
    background: #635bff !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
}

/* ── Floating action button ── */
.fab-wrap {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    z-index: 999;
}
.fab-wrap .stButton > button {
    width: auto !important;
    border-radius: 999px !important;
    padding: 0.7rem 1.3rem !important;
    font-size: 0.9rem !important;
    box-shadow: 0 6px 20px rgba(99,91,255,.45) !important;
}

/* ── Dialog / modal ── */
[data-testid="stDialog"] [data-testid="stVerticalBlock"] {
    gap: 0.6rem;
}
[data-testid="stDialogContent"] {
    border-radius: 16px !important;
    padding: 2rem !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ────────────────────────────────────────────────────
DEFAULTS = {
    "step": 1,
    "email_addr": "",
    "app_password": "",
    "report": None,
    "marked_cancellation": set(),
    "alert_telegram_token": "",
    "alert_telegram_chat_id": "",
    "alert_whatsapp_number": "",
    "alert_save_status": None,
    "budget_usd": 0.0,
    "budget_ngn": 0.0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Alert config ──────────────────────────────────────────────────────────────
ALERT_CONFIG_FILE = Path("alerts_config.json")

def load_alert_config():
    if ALERT_CONFIG_FILE.exists():
        try:
            cfg = json.loads(ALERT_CONFIG_FILE.read_text())
            st.session_state.alert_telegram_token   = cfg.get("telegram_token", "")
            st.session_state.alert_telegram_chat_id = cfg.get("telegram_chat_id", "")
            st.session_state.alert_whatsapp_number  = cfg.get("whatsapp_number", "")
            st.session_state.budget_usd = float(cfg.get("budget_usd", 0))
            st.session_state.budget_ngn = float(cfg.get("budget_ngn", 0))
        except Exception:
            pass

def save_alert_config(token, chat_id, wa_number):
    cfg = {}
    if ALERT_CONFIG_FILE.exists():
        try:
            cfg = json.loads(ALERT_CONFIG_FILE.read_text())
        except Exception:
            pass
    cfg.update({"telegram_token": token, "telegram_chat_id": chat_id, "whatsapp_number": wa_number})
    ALERT_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def save_budget(budget_usd: float, budget_ngn: float):
    cfg = {}
    if ALERT_CONFIG_FILE.exists():
        try:
            cfg = json.loads(ALERT_CONFIG_FILE.read_text())
        except Exception:
            pass
    cfg.update({"budget_usd": budget_usd, "budget_ngn": budget_ngn})
    ALERT_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def send_telegram_message(token, chat_id, text):
    try:
        import urllib.request
        token = token.strip(); chat_id = chat_id.strip()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            result = json.loads(resp.read())
            return (True, "") if result.get("ok") else (False, result.get("description", "Unknown error"))
    except Exception as exc:
        return False, str(exc)

def save_credentials(email, password):
    """Persist Gmail credentials to alerts_config.json."""
    cfg = {}
    if ALERT_CONFIG_FILE.exists():
        try:
            cfg = json.loads(ALERT_CONFIG_FILE.read_text())
        except Exception:
            pass
    cfg["email_addr"]   = email
    cfg["app_password"] = password
    ALERT_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def load_saved_credentials():
    """Auto-fill Gmail credentials from alerts_config.json if not already set."""
    if ALERT_CONFIG_FILE.exists():
        try:
            cfg = json.loads(ALERT_CONFIG_FILE.read_text())
            if cfg.get("email_addr") and not st.session_state.email_addr:
                st.session_state.email_addr   = cfg["email_addr"]
            if cfg.get("app_password") and not st.session_state.app_password:
                st.session_state.app_password = cfg["app_password"]
        except Exception:
            pass


# ── Renewal reminder deduplication ────────────────────────────────────────────
SENT_ALERTS_FILE = Path("sent_alerts.json")
REMINDER_DAYS    = [3, 2, 1]

def load_sent_alerts() -> dict:
    if SENT_ALERTS_FILE.exists():
        try:
            return json.loads(SENT_ALERTS_FILE.read_text())
        except Exception:
            pass
    return {}

def save_sent_alerts(sent: dict):
    SENT_ALERTS_FILE.write_text(json.dumps(sent, indent=2))

def check_and_send_renewal_reminders(report: dict) -> int:
    """
    Send Telegram reminders for renewals exactly 1, 2, or 3 days away.
    Skips alerts already sent (tracked in sent_alerts.json).
    Returns the number of new alerts sent.
    """
    tg_token   = st.session_state.alert_telegram_token.strip()
    tg_chat_id = st.session_state.alert_telegram_chat_id.strip()
    if not tg_token or not tg_chat_id:
        return 0

    renewals = report.get("upcoming_renewals_30d", [])
    today    = date.today()
    sent     = load_sent_alerts()
    count    = 0

    for r in renewals:
        days_until = r.get("days_until", 999)
        if days_until not in REMINDER_DAYS:
            continue
        alert_key = f"{r['renewal_date']}_{r['merchant']}_{days_until}"
        if alert_key in sent:
            continue
        day_word = "day" if days_until == 1 else "days"
        msg = (
            f"\u23f0 *Renewal Reminder \u2014 SubTrack*\n\n"
            f"*{r['merchant']}* renews in *{days_until} {day_word}* "
            f"({r['renewal_date']}).\n"
            f"Amount: *{r['currency']} {r['amount']:,.2f}*\n\n"
            f"If you don\u2019t wish to continue, cancel now."
        )
        ok, _ = send_telegram_message(tg_token, tg_chat_id, msg)
        if ok:
            sent[alert_key] = today.isoformat()
            count += 1

    if count:
        save_sent_alerts(sent)
    return count


def build_renewal_alert_text(report):
    lines = ["*SubTrack — Subscription Summary*\n"]
    spend_by_currency = report.get("spend_by_currency", {})
    count = report.get("merchant_count", 0)
    SYMS  = {"USD": "$", "NGN": "₦", "GBP": "£", "EUR": "€"}
    lines.append(f"📊 *{count} active subscription{'s' if count != 1 else ''}*")
    if spend_by_currency:
        lines.append("💳 Monthly spend: *" + " · ".join(
            f"{SYMS.get(c,c)}{a:,.2f}/mo" for c, a in spend_by_currency.items()
        ) + "*")
    for m in report.get("merchants", []):
        lines.append(f"• {m['merchant']} — {m['currency']} {m['monthly_cost']:,.2f}/mo")
    renewals = report.get("upcoming_renewals_30d", [])
    if renewals:
        lines.append("\n*⏰ Upcoming renewals (30 days):*")
        for r in renewals:
            lines.append(f"• *{r['merchant']}* — {r['currency']} {r['amount']:,.2f} in {r['days_until']}d ({r['renewal_date']})")
    else:
        lines.append("\n✅ No renewals due in the next 30 days")
    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────
def go_to(step):
    st.session_state.step = step

def render_step_bar(current):
    labels = ["1 · Connect", "2 · Scanning", "3 · Results", "4 · Actions"]
    html = '<div class="step-bar">'
    for i, label in enumerate(labels, 1):
        cls = "active" if i == current else ("done" if i < current else "")
        html += f'<div class="step {cls}">{label}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def render_header():
    st.markdown(
        '<div class="app-logo">'
        '<div class="app-logo-icon">💳</div>'
        '<span class="app-title">SubTrack</span>'
        '</div>'
        '<div class="app-subtitle">Subscription intelligence for your inbox</div>',
        unsafe_allow_html=True,
    )

CURRENCY_SYMBOLS = {"USD": "$", "NGN": "₦", "GBP": "£", "EUR": "€", "CAD": "CA$", "JPY": "¥"}
def fmt(currency, amount):
    sym = CURRENCY_SYMBOLS.get(currency, currency + " ")
    return f"{sym}{amount:,.2f}"


# ── Merchant logo helpers ─────────────────────────────────────────────────────
MERCHANT_DOMAINS = {
    # Streaming video
    "netflix": "netflix.com", "hulu": "hulu.com", "disney": "disneyplus.com",
    "hbo": "hbo.com", "max": "max.com", "peacock": "peacocktv.com",
    "paramount": "paramountplus.com", "crunchyroll": "crunchyroll.com",
    "prime video": "amazon.com", "amazon prime": "amazon.com",
    "apple tv": "tv.apple.com",
    # Music
    "spotify": "spotify.com", "tidal": "tidal.com", "deezer": "deezer.com",
    "pandora": "pandora.com", "soundcloud": "soundcloud.com",
    "youtube music": "music.youtube.com", "apple music": "music.apple.com",
    # AI Tools
    "openai": "openai.com", "anthropic": "anthropic.com", "claude": "claude.ai",
    "gemini": "gemini.google.com", "midjourney": "midjourney.com",
    "perplexity": "perplexity.ai", "jasper": "jasper.ai",
    "writesonic": "writesonic.com", "copilot": "microsoft.com",
    # Dev / Project management
    "github": "github.com", "gitlab": "gitlab.com", "jira": "atlassian.com",
    "confluence": "atlassian.com", "notion": "notion.so", "linear": "linear.app",
    "asana": "asana.com", "trello": "trello.com", "basecamp": "basecamp.com",
    "monday": "monday.com",
    # Cloud hosting / infra
    "vercel": "vercel.com", "netlify": "netlify.com", "heroku": "heroku.com",
    "digitalocean": "digitalocean.com", "render": "render.com",
    "railway": "railway.app", "aws": "aws.amazon.com",
    "azure": "azure.microsoft.com", "gcp": "cloud.google.com",
    # Cloud storage
    "dropbox": "dropbox.com", "google one": "one.google.com",
    "icloud": "icloud.com", "onedrive": "microsoft.com",
    "backblaze": "backblaze.com", "box": "box.com",
    # Design
    "adobe": "adobe.com", "figma": "figma.com", "canva": "canva.com",
    "sketch": "sketch.com", "invision": "invisionapp.com",
    # Communication
    "zoom": "zoom.us", "slack": "slack.com", "loom": "loom.com",
    "webex": "webex.com",
    # Security
    "nordvpn": "nordvpn.com", "expressvpn": "expressvpn.com",
    "surfshark": "surfshark.com", "protonvpn": "protonvpn.com",
    "1password": "1password.com", "lastpass": "lastpass.com",
    "dashlane": "dashlane.com", "bitwarden": "bitwarden.com",
    # Productivity / Writing
    "grammarly": "grammarly.com", "notion": "notion.so",
    # Education
    "duolingo": "duolingo.com", "coursera": "coursera.org",
    "udemy": "udemy.com", "pluralsight": "pluralsight.com",
    "masterclass": "masterclass.com",
    # News / Media
    "nytimes": "nytimes.com", "wsj": "wsj.com", "medium": "medium.com",
    "substack": "substack.com", "bloomberg": "bloomberg.com",
    "economist": "economist.com",
    # Website builders / ecom
    "shopify": "shopify.com", "squarespace": "squarespace.com",
    "wix": "wix.com", "wordpress": "wordpress.com", "webflow": "webflow.com",
    # Accounting
    "xero": "xero.com", "quickbooks": "quickbooks.intuit.com",
    "freshbooks": "freshbooks.com",
    # Misc / well-known
    "starlink": "starlink.com", "linkedin": "linkedin.com",
    "youtube": "youtube.com", "apple": "apple.com",
    "google": "google.com", "microsoft": "microsoft.com",
    "amazon": "amazon.com", "twitter": "twitter.com", "x.com": "x.com",
    "twitch": "twitch.tv", "patreon": "patreon.com",
    "protonmail": "proton.me", "fastmail": "fastmail.com",
}

def get_merchant_favicon(merchant: str) -> str:
    """Return Google-favicon URL for the closest known domain, or '' if unknown."""
    lower = merchant.lower()
    # Exact or partial keyword match (longest keyword wins to avoid 'max'→'max.com' being trumped)
    best_kw, best_domain = "", ""
    for kw, domain in MERCHANT_DOMAINS.items():
        if kw in lower and len(kw) > len(best_kw):
            best_kw, best_domain = kw, domain
    if best_domain:
        return f"https://www.google.com/s2/favicons?domain={best_domain}&sz=64"
    return ""

def sub_icon_html(merchant: str, fallback_emoji: str) -> str:
    """Return the <div class='sub-icon'> block, with brand logo or emoji fallback."""
    favicon = get_merchant_favicon(merchant)
    if favicon:
        return (
            f'<div class="sub-icon" style="padding:0;overflow:hidden;background:#fff;">'
            f'<img src="{favicon}" width="28" height="28" style="border-radius:6px;display:block;margin:auto;" '
            f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\';">'
            f'<span style="display:none;width:100%;height:100%;align-items:center;justify-content:center;font-size:1rem;">{fallback_emoji}</span>'
            f'</div>'
        )
    return f'<div class="sub-icon">{fallback_emoji}</div>'


# ── Cancellation links ────────────────────────────────────────────────────────
CANCELLATION_LINKS: dict[str, str] = {
    "netflix":      "https://www.netflix.com/cancel",
    "spotify":      "https://www.spotify.com/account/subscription/",
    "hulu":         "https://secure.hulu.com/account/cancel",
    "disney":       "https://www.disneyplus.com/account",
    "hbo":          "https://www.max.com/account",
    "max":          "https://www.max.com/account",
    "peacock":      "https://www.peacocktv.com/account",
    "paramount":    "https://www.paramountplus.com/account/",
    "apple tv":     "https://support.apple.com/en-us/118428",
    "apple music":  "https://support.apple.com/en-us/118428",
    "apple":        "https://appleid.apple.com/account/manage",
    "youtube":      "https://youtube.com/paid_memberships",
    "amazon":       "https://www.amazon.com/mc/pipelines/cancellation",
    "spotify":      "https://www.spotify.com/account/subscription/",
    "tidal":        "https://listen.tidal.com/account/subscription",
    "deezer":       "https://www.deezer.com/en/account/premium-subscription",
    "openai":       "https://platform.openai.com/account/billing",
    "anthropic":    "https://console.anthropic.com/settings/billing",
    "claude":       "https://console.anthropic.com/settings/billing",
    "gemini":       "https://one.google.com/about",
    "midjourney":   "https://www.midjourney.com/account/",
    "perplexity":   "https://www.perplexity.ai/settings",
    "grammarly":    "https://account.grammarly.com/subscription",
    "notion":       "https://www.notion.so/profile/plans",
    "github":       "https://github.com/settings/billing",
    "gitlab":       "https://gitlab.com/-/profile/billing",
    "jira":         "https://admin.atlassian.com/",
    "confluence":   "https://admin.atlassian.com/",
    "asana":        "https://app.asana.com/-/account_api",
    "trello":       "https://trello.com/billing",
    "monday":       "https://auth.monday.com/login",
    "linear":       "https://linear.app/settings/subscription",
    "dropbox":      "https://www.dropbox.com/account/plan",
    "google one":   "https://one.google.com/about",
    "adobe":        "https://account.adobe.com/plans",
    "figma":        "https://www.figma.com/settings",
    "canva":        "https://www.canva.com/settings/plans-and-billing",
    "zoom":         "https://zoom.us/billing",
    "slack":        "https://slack.com/intl/en-us/help/articles/204369004",
    "nordvpn":      "https://my.nordaccount.com/subscription/",
    "expressvpn":   "https://www.expressvpn.com/subscriptions",
    "surfshark":    "https://my.surfshark.com/subscriptions",
    "1password":    "https://my.1password.com/profile",
    "lastpass":     "https://lastpass.com/",
    "dashlane":     "https://app.dashlane.com/login",
    "bitwarden":    "https://vault.bitwarden.com/",
    "shopify":      "https://admin.shopify.com/settings/billing",
    "squarespace":  "https://account.squarespace.com/subscriptions",
    "wordpress":    "https://wordpress.com/purchases",
    "webflow":      "https://webflow.com/account",
    "wix":          "https://manage.wix.com/premium-purchase-plan/dynamo",
    "duolingo":     "https://www.duolingo.com/settings",
    "coursera":     "https://www.coursera.org/account-profile#subscriptions",
    "udemy":        "https://www.udemy.com/dashboard/subscription",
    "masterclass":  "https://www.masterclass.com/account/subscription",
    "linkedin":     "https://www.linkedin.com/premium/manage/cancel",
    "nytimes":      "https://www.nytimes.com/subscription",
    "medium":       "https://medium.com/me/membership",
    "substack":     "https://substack.com/settings",
    "bloomberg":    "https://www.bloomberg.com/account/",
    "xero":         "https://go.xero.com/Settings/Subscription",
    "quickbooks":   "https://accounts.intuit.com/",
    "vercel":       "https://vercel.com/account/billing",
    "netlify":      "https://app.netlify.com/teams/user/billing/subscriptions",
    "digitalocean": "https://cloud.digitalocean.com/account/billing",
    "heroku":       "https://dashboard.heroku.com/account/billing",
    "starlink":     "https://www.starlink.com/account",
    "microsoft":    "https://account.microsoft.com/services/",
    "google":       "https://myaccount.google.com/payments-and-subscriptions",
    "patreon":      "https://www.patreon.com/settings/memberships",
    "twitch":       "https://www.twitch.tv/settings/prime",
    "loom":         "https://www.loom.com/account",
    "notion":       "https://www.notion.so/profile/plans",
}

def get_cancellation_link(merchant: str) -> str:
    """Return a direct cancellation URL for known services, or '' if unknown."""
    lower = merchant.lower()
    best_kw, best_url = "", ""
    for kw, url in CANCELLATION_LINKS.items():
        if kw in lower and len(kw) > len(best_kw):
            best_kw, best_url = kw, url
    return best_url


# ── Dialogs (modals) ──────────────────────────────────────────────────────────
@st.dialog("➕ Add Subscription Manually", width="large")
def dialog_add_subscription():
    st.markdown(
        '<p style="color:#8898aa;font-size:0.83rem;margin-bottom:1rem;">'
        "Add subscriptions not in email — gym, bank debits, Apple Pay, etc.</p>",
        unsafe_allow_html=True,
    )
    mc1, mc2 = st.columns(2)
    with mc1:
        manual_merchant = st.text_input("Service name", placeholder="e.g. Gym membership")
        manual_amount   = st.number_input("Amount", min_value=0.01, value=9.99, step=0.01, format="%.2f")
    with mc2:
        manual_currency = st.selectbox("Currency", ["USD", "NGN", "GBP", "EUR"])
        manual_freq     = st.selectbox("Billing cycle", ["monthly", "yearly", "quarterly"])
    manual_date = st.date_input("Start / last billing date", value=date.today())

    save_col, cancel_col = st.columns(2)
    with save_col:
        if st.button("Add Subscription", type="primary", use_container_width=True):
            if not manual_merchant.strip():
                st.error("Please enter a service name.")
            else:
                import hashlib as _hl
                from datetime import datetime as _dt, timezone as _tz
                record = {
                    "id":                _hl.sha256(f"manual:{manual_merchant}:{manual_amount}:{manual_date}".encode()).hexdigest()[:16],
                    "merchant":          manual_merchant.strip(),
                    "amount":            round(float(manual_amount), 2),
                    "currency":          manual_currency,
                    "date":              manual_date.isoformat(),
                    "subject":           f"Manual entry: {manual_merchant.strip()}",
                    "source_email":      "manual",
                    "detected_keywords": [],
                    "status":            "active",
                    "source":            "manual",
                    "frequency_override": manual_freq,
                    "parsed_at":         _dt.now(_tz.utc).isoformat(),
                }
                with Path("subscriptions.jsonl").open("a") as _f:
                    _f.write(json.dumps(record) + "\n")
                from analyzer import run_analysis
                st.session_state.report = run_analysis()
                st.success(f"Added **{manual_merchant.strip()}** ({manual_currency} {manual_amount:,.2f}/{manual_freq}).")
                st.rerun()
    with cancel_col:
        if st.button("Cancel", type="secondary", use_container_width=True):
            st.rerun()


@st.dialog("💰 Monthly Budget Limits", width="small")
def dialog_budget():
    st.markdown(
        '<p style="color:#8898aa;font-size:0.83rem;margin-bottom:1rem;">'
        "Get a warning when your total monthly spend exceeds these limits.</p>",
        unsafe_allow_html=True,
    )
    b_usd = st.number_input("USD limit ($/mo)",  min_value=0.0, value=float(st.session_state.budget_usd), step=5.0,    format="%.2f")
    b_ngn = st.number_input("NGN limit (₦/mo)",  min_value=0.0, value=float(st.session_state.budget_ngn), step=1000.0, format="%.2f")
    st.markdown('<p style="color:#8898aa;font-size:0.76rem;">Set to 0 to disable a limit.</p>', unsafe_allow_html=True)

    save_col, cancel_col = st.columns(2)
    with save_col:
        if st.button("Save Budget", type="primary", use_container_width=True):
            st.session_state.budget_usd = b_usd
            st.session_state.budget_ngn = b_ngn
            save_budget(b_usd, b_ngn)
            report = st.session_state.report or {}
            spend  = report.get("spend_by_currency", {})
            tg_tok = st.session_state.alert_telegram_token.strip()
            tg_cid = st.session_state.alert_telegram_chat_id.strip()
            if b_usd and spend.get("USD", 0) > b_usd and tg_tok and tg_cid:
                send_telegram_message(tg_tok, tg_cid,
                    f"⚠️ *Over USD budget!* ${spend['USD']:,.2f}/mo vs ${b_usd:,.2f} limit.")
            if b_ngn and spend.get("NGN", 0) > b_ngn and tg_tok and tg_cid:
                send_telegram_message(tg_tok, tg_cid,
                    f"⚠️ *Over NGN budget!* ₦{spend['NGN']:,.2f}/mo vs ₦{b_ngn:,.2f} limit.")
            st.success("Budget saved.")
            st.rerun()
    with cancel_col:
        if st.button("Cancel", type="secondary", use_container_width=True):
            st.rerun()


# ── STEP 1: Connect ───────────────────────────────────────────────────────────
def render_connect():
    st.markdown(
        '<div class="card">'
        '<div class="card-title">Connect your Gmail</div>'
        '<div class="card-desc">We use read-only IMAP with an App Password — your credentials never leave this machine.</div>',
        unsafe_allow_html=True,
    )

    email_val    = st.text_input("Gmail address", value=st.session_state.email_addr,    placeholder="you@gmail.com",         key="input_email")
    password_val = st.text_input("App Password",  value=st.session_state.app_password,  placeholder="xxxx xxxx xxxx xxxx",   key="input_pw", type="password")

    st.markdown(
        '<p style="color:#8898aa;font-size:0.76rem;margin-top:-0.4rem;margin-bottom:1rem;">'
        'Generate one at <strong style="color:#525f7f;">myaccount.google.com → Security → App passwords</strong>'
        '</p>',
        unsafe_allow_html=True,
    )

    if st.button("Connect & Scan Inbox", key="btn_connect"):
        if not email_val or "@" not in email_val:
            st.error("Please enter a valid Gmail address.")
        elif not password_val or len(password_val.replace(" ", "")) < 12:
            st.error("App Password looks too short — it should be 16 characters.")
        else:
            st.session_state.email_addr   = email_val
            st.session_state.app_password = password_val
            save_credentials(email_val, password_val)
            st.session_state.scan = {
                "progress": 0, "total": 1, "logs": [],
                "done": False, "error": None, "report": None,
                "started": False, "cancelled": False,
            }
            go_to(2)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="info-grid">'
        '<div class="info-card"><div class="info-icon">🔒</div>'
        '<div class="info-title">Read-only access</div>'
        '<div class="info-desc">We never send, delete, or modify your emails.</div></div>'
        '<div class="info-card"><div class="info-icon">💾</div>'
        '<div class="info-title">Stays on your machine</div>'
        '<div class="info-desc">Results saved locally in subscriptions.jsonl.</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-top:1.25rem;'></div>", unsafe_allow_html=True)
    if st.button("➕ Add subscription manually", type="secondary", use_container_width=True, key="btn_add_manual_connect"):
        dialog_add_subscription()


# ── STEP 2: Scanning ──────────────────────────────────────────────────────────
def render_scanning():
    from parser import run_parser

    email_addr   = st.session_state.get("email_addr", "")
    app_password = st.session_state.get("app_password", "")

    if not email_addr:
        st.error("No credentials found. Please go back and connect your Gmail.")
        if st.button("← Back"):
            go_to(1); st.rerun()
        return

    if "scan" not in st.session_state:
        st.session_state.scan = {
            "progress": 0, "total": 1, "logs": [],
            "done": False, "error": None, "report": None,
            "started": False, "cancelled": False,
        }
    scan = st.session_state.scan

    def progress_cb(current, total, record):
        scan["progress"] = current
        scan["total"]    = max(total, 1)
        merchant = record.get("merchant", "Unknown")
        amount   = record.get("amount")
        currency = record.get("currency", "USD")
        amt_str  = f"{currency} {amount:,.2f}" if amount else "—"
        scan["logs"].append(f"✔  {merchant}  ·  {amt_str}  ·  {record.get('date','')}")
        if scan["cancelled"]:
            raise InterruptedError("Scan cancelled.")

    def do_scan():
        try:
            run_parser(email_addr, app_password, progress_callback=progress_cb)
            from analyzer import run_analysis
            scan["report"] = run_analysis()
        except InterruptedError:
            scan["logs"].append("⚠  Scan cancelled by user.")
        except Exception as exc:
            scan["error"] = str(exc)
        finally:
            scan["done"] = True

    if not scan["started"]:
        scan["started"] = True
        threading.Thread(target=do_scan, daemon=True).start()

    progress_placeholder = st.empty()
    log_placeholder      = st.empty()

    if not scan["done"]:
        pct = scan["progress"] / max(scan["total"], 1)
        pct_pct = int(pct * 100)
        with progress_placeholder.container():
            st.markdown(
                '<div class="card" style="text-align:center;padding:2rem 1.75rem 1.5rem;">'
                '<div class="scan-wrap" style="padding:0 0 1rem;">'
                '<div class="scan-spinner"></div>'
                f'<div class="scan-label">Scanning your inbox</div>'
                f'<div style="font-size:0.75rem;color:#8898aa;margin-top:0.35rem;">{scan["progress"]} of {scan["total"]} emails · {pct_pct}%</div>'
                '</div>'
                f'<div style="background:#e3e8ee;border-radius:999px;height:6px;overflow:hidden;">'
                f'<div style="background:#635bff;width:{pct_pct}%;height:100%;border-radius:999px;transition:width 0.4s ease;"></div>'
                f'</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        log_html = (
            '<div class="log-box">'
            + ("<br>".join(scan["logs"][-30:]) or '<span style="color:#8898aa;">Connecting to Gmail…</span>')
            + "</div>"
        )
        log_placeholder.markdown(log_html, unsafe_allow_html=True)

        back_col, _, cancel_col = st.columns([1, 2, 1])
        with back_col:
            if st.button("← Back", key="btn_back_scan"):
                scan["cancelled"] = True
                if "scan" in st.session_state: del st.session_state["scan"]
                go_to(1); st.rerun()
        with cancel_col:
            if st.button("Cancel scan", key="btn_cancel_scan"):
                scan["cancelled"] = True
        time.sleep(0.5)
        st.rerun()
        return

    # ── Done ──────────────────────────────────────────────────────────────
    if scan["error"]:
        st.error(f"Scan error: {scan['error']}")
        if st.button("← Try again"):
            del st.session_state["scan"]; go_to(1); st.rerun()
        return

    if scan["report"]:
        st.session_state.report = scan["report"]

    load_alert_config()
    tg_token   = st.session_state.alert_telegram_token.strip()
    tg_chat_id = st.session_state.alert_telegram_chat_id.strip()
    if tg_token and tg_chat_id and scan["report"] and not scan.get("alert_sent"):
        ok, _ = send_telegram_message(tg_token, tg_chat_id, build_renewal_alert_text(scan["report"]))
        scan["alert_sent"] = True
        if ok:
            st.toast("Telegram alert sent!", icon="✅")

    with progress_placeholder.container():
        st.markdown(
            '<div class="card" style="text-align:center;border-top:3px solid #2dce89;padding:2rem 1.75rem 1.5rem;">'
            '<div style="font-size:2rem;margin-bottom:0.5rem;">✅</div>'
            '<div style="font-weight:600;color:#32325d;font-size:1rem;margin-bottom:1rem;">Scan complete</div>'
            '<div style="background:#e3e8ee;border-radius:999px;height:6px;overflow:hidden;">'
            '<div style="background:#2dce89;width:100%;height:100%;border-radius:999px;"></div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    log_html = '<div class="log-box">' + "<br>".join(scan["logs"][-30:]) + "</div>"
    log_placeholder.markdown(log_html, unsafe_allow_html=True)

    report = st.session_state.report or {}
    st.success(
        f"Found **{report.get('total_records', 0)}** subscription emails "
        f"from **{report.get('merchant_count', 0)}** merchants."
    )
    if st.button("View Results →"):
        go_to(3); st.rerun()


# ── STEP 3: Results ───────────────────────────────────────────────────────────
def render_results():
    report = st.session_state.report
    if not report:
        st.warning("No report yet — please run the scanner first.")
        if st.button("← Back"):
            go_to(1); st.rerun()
        return

    spend_by_currency = report.get("spend_by_currency", {})
    savings      = report.get("potential_monthly_savings", 0)
    renewals_30d = len(report.get("upcoming_renewals_30d", []))

    monthly_str = " · ".join(fmt(c, a) for c, a in spend_by_currency.items()) if spend_by_currency else "$0.00"
    yearly_str  = " · ".join(fmt(c, round(a*12,2)) for c, a in spend_by_currency.items()) if spend_by_currency else "$0.00"

    # ── Top navigation ─────────────────────────────────────────────────────
    st.markdown('<div class="nav-row">', unsafe_allow_html=True)
    nav_l, nav_mid1, nav_mid2, nav_r = st.columns([2, 1, 1, 2])
    with nav_l:
        if st.button("← Re-scan", key="btn_rescan_top", type="secondary", use_container_width=True):
            if "scan" in st.session_state: del st.session_state["scan"]
            go_to(1); st.rerun()
    with nav_mid1:
        if st.button("➕ Add", key="btn_add_top", type="secondary", use_container_width=True):
            dialog_add_subscription()
    with nav_mid2:
        if st.button("💰 Budget", key="btn_budget_top", type="secondary", use_container_width=True):
            dialog_budget()
    with nav_r:
        if st.button("Take Action →", key="btn_action_top", type="primary", use_container_width=True):
            go_to(4); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)

    # ── Stat cards ─────────────────────────────────────────────────────────
    st.markdown(f"""
<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-label">Monthly spend</div>
    <div class="stat-value purple" style="font-size:1.3rem;">{monthly_str}</div>
    <div class="stat-sub">{yearly_str} / yr</div>
  </div>
  <div class="stat-card green">
    <div class="stat-label">Potential savings</div>
    <div class="stat-value green">${savings:,.2f}<span style="font-size:0.85rem;font-weight:500">/mo</span></div>
    <div class="stat-sub">from duplicate services</div>
  </div>
  <div class="stat-card orange">
    <div class="stat-label">Renewals · 30 days</div>
    <div class="stat-value orange">{renewals_30d}</div>
    <div class="stat-sub">upcoming charges</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Budget warning ─────────────────────────────────────────────────────
    budget_usd = st.session_state.get("budget_usd", 0) or 0
    budget_ngn = st.session_state.get("budget_ngn", 0) or 0
    usd_spend  = spend_by_currency.get("USD", 0)
    ngn_spend  = spend_by_currency.get("NGN", 0)
    if budget_usd and usd_spend > budget_usd:
        over = usd_spend - budget_usd
        st.markdown(
            f'<div style="background:rgba(245,54,92,.07);border:1px solid rgba(245,54,92,.25);'
            f'border-left:4px solid #f5365c;border-radius:10px;padding:0.9rem 1.2rem;margin-bottom:1rem;">'
            f'<span style="color:#f5365c;font-weight:700;">⚠ Over budget!</span> '
            f'<span style="color:#525f7f;">You\'re spending <strong>${usd_spend:,.2f}/mo</strong> '
            f'vs your <strong>${budget_usd:,.2f}</strong> limit — '
            f'<strong style="color:#f5365c;">${over:,.2f} over.</strong></span></div>',
            unsafe_allow_html=True,
        )
    if budget_ngn and ngn_spend > budget_ngn:
        over = ngn_spend - budget_ngn
        st.markdown(
            f'<div style="background:rgba(245,54,92,.07);border:1px solid rgba(245,54,92,.25);'
            f'border-left:4px solid #f5365c;border-radius:10px;padding:0.9rem 1.2rem;margin-bottom:1rem;">'
            f'<span style="color:#f5365c;font-weight:700;">⚠ Over budget!</span> '
            f'<span style="color:#525f7f;">You\'re spending <strong>₦{ngn_spend:,.2f}/mo</strong> '
            f'vs your <strong>₦{budget_ngn:,.2f}</strong> limit — '
            f'<strong style="color:#f5365c;">₦{over:,.2f} over.</strong></span></div>',
            unsafe_allow_html=True,
        )

    # ── Spending charts ────────────────────────────────────────────────────
    monthly_trend      = report.get("monthly_trend", {})
    category_breakdown = report.get("category_breakdown", [])
    if monthly_trend or category_breakdown:
        import plotly.graph_objects as go
        st.markdown('<div class="section-header">📈 Spending Analytics</div>', unsafe_allow_html=True)
        ch_left, ch_right = st.columns([3, 2])

        # Monthly bar chart — show USD (most likely to have multiple months)
        trend_data = monthly_trend.get("USD") or next(iter(monthly_trend.values()), None)
        with ch_left:
            if trend_data and len(trend_data) >= 1:
                currency_label = next(
                    (c for c, d in monthly_trend.items() if d is trend_data), "USD"
                )
                sym = CURRENCY_SYMBOLS.get(currency_label, currency_label + " ")
                months  = [t["month"] for t in trend_data]
                amounts = [t["amount"] for t in trend_data]
                fig = go.Figure(go.Bar(
                    x=months, y=amounts,
                    marker_color="#635bff",
                    hovertemplate=f"<b>%{{x}}</b><br>{sym}%{{y:,.2f}}<extra></extra>",
                ))
                fig.update_layout(
                    title=dict(text=f"Monthly Charges ({currency_label})", font=dict(size=12, color="#525f7f")),
                    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                    margin=dict(l=0, r=0, t=36, b=0), height=220,
                    font=dict(family="sans-serif", color="#525f7f", size=11),
                    yaxis=dict(gridcolor="#e3e8ee", zeroline=False, tickprefix=sym),
                    xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    bargap=0.35,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Category donut
        with ch_right:
            cats = [c["category"] for c in category_breakdown if c["monthly_cost"] > 0]
            vals = [c["monthly_cost"] for c in category_breakdown if c["monthly_cost"] > 0]
            if cats:
                CHART_COLORS = [
                    "#635bff","#2dce89","#fb6340","#f5365c","#11cdef",
                    "#ffd600","#8898aa","#344675","#adb5bd","#0c6dfd",
                ]
                fig2 = go.Figure(go.Pie(
                    labels=cats, values=vals, hole=0.58,
                    marker=dict(colors=CHART_COLORS[:len(cats)], line=dict(color="#ffffff", width=2)),
                    textinfo="percent",
                    hovertemplate="<b>%{label}</b><br>$%{value:,.2f}/mo<extra></extra>",
                ))
                fig2.update_layout(
                    title=dict(text="By Category", font=dict(size=12, color="#525f7f")),
                    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                    margin=dict(l=0, r=0, t=36, b=0), height=220,
                    font=dict(family="sans-serif", color="#525f7f", size=10),
                    showlegend=False,
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Overlaps ───────────────────────────────────────────────────────────
    overlaps = report.get("overlaps", [])
    if overlaps:
        st.markdown('<div class="section-header">⚠ Duplicate Subscriptions</div>', unsafe_allow_html=True)
        for ov in overlaps:
            st.markdown(f"""
<div class="overlap-card">
  <div class="overlap-title">Duplicate detected · {ov['category']}</div>
  <div class="overlap-desc">
    <strong style="color:#32325d">{ov['merchant_a']}</strong> (${ov['monthly_cost_a']}/mo) &amp;
    <strong style="color:#32325d">{ov['merchant_b']}</strong> (${ov['monthly_cost_b']}/mo) — {ov['reason']}
    <br><span style="color:#f5365c;font-weight:600;font-size:0.83rem;">Save ${ov['potential_savings']:.2f}/mo by cancelling one</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Upcoming renewals ──────────────────────────────────────────────────
    renewals = report.get("upcoming_renewals_30d", [])
    if renewals:
        st.markdown('<div class="section-header">🔔 Upcoming Renewals</div>', unsafe_allow_html=True)
        for r in renewals:
            days_label = f"in {r['days_until']} day{'s' if r['days_until'] != 1 else ''}"
            st.markdown(f"""
<div class="sub-row">
  <div style="display:flex;align-items:center;gap:0.75rem;">
    {sub_icon_html(r['merchant'], "📅")}
    <div>
      <div class="sub-merchant">{r['merchant']}</div>
      <div class="sub-category">{r['renewal_date']}</div>
    </div>
  </div>
  <div style="text-align:right">
    <div class="sub-amount">{fmt(r['currency'], r['amount'])}</div>
    <div><span class="renewal-pill">{days_label}</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── All subscriptions ──────────────────────────────────────────────────
    merchants = report.get("merchants", [])
    ICONS = {
        "Streaming Video": "🎬", "Music Streaming": "🎵", "AI Tools": "🤖",
        "Cloud Storage": "☁️", "Dev / Project Mgmt": "⚙️", "Design Tools": "🎨",
        "Cloud Hosting": "🖥", "Communication": "💬", "News / Media": "📰",
        "Education": "📚", "VPN": "🔐", "Accounting": "📊",
    }
    st.markdown(f'<div class="section-header">📋 All Subscriptions ({len(merchants)})</div>', unsafe_allow_html=True)

    for m in merchants:
        freq_label = m.get("frequency") or "—"
        icon = ICONS.get(m.get("category",""), "💳")
        forgotten_badge = (
            f'<span class="badge badge-warning" style="margin-left:6px;">Forgotten</span>'
            if m.get("is_forgotten") else ""
        )
        st.markdown(f"""
<div class="sub-row">
  <div style="display:flex;align-items:center;gap:0.75rem;flex:1;min-width:0;">
    {sub_icon_html(m['merchant'], icon)}
    <div style="min-width:0;">
      <div class="sub-merchant">{m['merchant']}{forgotten_badge}</div>
      <div class="sub-category">{m['category']} · {m['charge_count']} charge{'s' if m['charge_count']!=1 else ''} · last {m.get('last_charge','?')}</div>
    </div>
  </div>
  <div style="text-align:right;white-space:nowrap;">
    <div class="sub-amount">{fmt(m['currency'], m['monthly_cost'])}<span style="font-size:0.72rem;color:#8898aa;font-weight:400">/mo</span></div>
    <div class="sub-freq">{freq_label}</div>
  </div>
</div>
""", unsafe_allow_html=True)
        checked = st.checkbox(
            f"Mark {m['merchant']} for cancellation",
            key=f"cancel_{m['merchant']}",
            value=(m["merchant"] in st.session_state.marked_cancellation),
        )
        if checked: st.session_state.marked_cancellation.add(m["merchant"])
        else:        st.session_state.marked_cancellation.discard(m["merchant"])

    # ── Forgotten ──────────────────────────────────────────────────────────
    forgotten = report.get("forgotten_subscriptions", [])
    if forgotten:
        st.markdown(f'<div class="section-header">👻 Forgotten Subscriptions ({len(forgotten)})</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#8898aa;font-size:0.83rem;margin-bottom:0.75rem;">Charged but no email in over 90 days.</p>', unsafe_allow_html=True)
        for m in forgotten:
            st.markdown(f"""
<div class="sub-row" style="border-left:3px solid #fb6340;">
  <div style="display:flex;align-items:center;gap:0.75rem;">
    {sub_icon_html(m['merchant'], "👻")}
    <div>
      <div class="sub-merchant">{m['merchant']} <span class="badge badge-warning">No email in {m['days_since_last']}d</span></div>
      <div class="sub-category">{m['category']}</div>
    </div>
  </div>
  <div style="text-align:right">
    <div class="sub-amount">{fmt(m['currency'], m['monthly_cost'])}/mo</div>
    <div class="sub-freq">{m.get('frequency','?')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Recently cancelled ──────────────────────────────────────────────────
    cancelled = report.get("recently_cancelled", [])
    if cancelled:
        st.markdown(f'<div class="section-header">↩️ Recently Cancelled ({len(cancelled)})</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#8898aa;font-size:0.83rem;margin-bottom:0.75rem;">Want any of these back?</p>', unsafe_allow_html=True)
        for c in cancelled:
            amt_str    = fmt(c['currency'], c['last_amount']) + "/mo" if c.get("last_amount") else "—"
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(c['merchant'] + ' subscribe')}"
            st.markdown(f"""
<div class="sub-row" style="border-left:3px solid #635bff;">
  <div style="display:flex;align-items:center;gap:0.75rem;flex:1;min-width:0;">
    {sub_icon_html(c['merchant'], "↩️")}
    <div>
      <div class="sub-merchant">{c['merchant']} <span class="badge badge-info">Cancelled</span></div>
      <div class="sub-category">{c['category']} · last seen {c.get('cancelled_date','?')}</div>
    </div>
  </div>
  <div style="text-align:right;white-space:nowrap;">
    <div class="sub-amount" style="color:#8898aa;">{amt_str}</div>
    <a href="{search_url}" target="_blank" style="font-size:0.72rem;color:#635bff;font-weight:600;text-decoration:none;">↗ Resubscribe</a>
  </div>
</div>
""", unsafe_allow_html=True)



# ── STEP 4: Actions ───────────────────────────────────────────────────────────
def render_actions():
    report = st.session_state.report or {}
    marked = list(st.session_state.marked_cancellation)

    # ── Export ────────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Export & Actions</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📄 Audit Report</div>', unsafe_allow_html=True)
    st.download_button(
        label="Download report.json",
        data=json.dumps(report, indent=2),
        file_name="subscription_audit.json",
        mime="application/json",
        key="dl_json",
    )

    # ── Cancellation with direct links ───────────────────────────────────
    st.markdown('<div class="section-header">🗑 Cancel Subscriptions</div>', unsafe_allow_html=True)
    if not marked:
        st.markdown(
            '<p style="color:#8898aa;font-size:0.85rem;">No subscriptions marked for cancellation yet. '
            'Go back to Results and check the boxes next to services you want to cancel.</p>',
            unsafe_allow_html=True,
        )
    else:
        merchants_info = {m["merchant"]: m for m in report.get("merchants", [])}
        total = sum(merchants_info.get(n, {}).get("monthly_cost", 0) for n in marked)
        st.success(f"Cancelling **{len(marked)}** subscription{'s' if len(marked)!=1 else ''} saves **${total:.2f}/month** (${total*12:.2f}/year).")
        for name in marked:
            info      = merchants_info.get(name, {})
            cancel_url = get_cancellation_link(name)
            amt_str   = fmt(info.get("currency","USD"), info.get("monthly_cost", 0)) + "/mo"
            link_html = (
                f'<a href="{cancel_url}" target="_blank" style="font-size:0.78rem;font-weight:600;'
                f'color:#f5365c;text-decoration:none;white-space:nowrap;">↗ Cancel now</a>'
                if cancel_url else
                f'<a href="https://www.google.com/search?q={urllib.parse.quote(name+" cancel subscription")}" '
                f'target="_blank" style="font-size:0.78rem;font-weight:600;color:#8898aa;text-decoration:none;">↗ Find page</a>'
            )
            st.markdown(f"""
<div class="sub-row">
  <div style="display:flex;align-items:center;gap:0.75rem;flex:1;min-width:0;">
    {sub_icon_html(name, "🗑")}
    <div>
      <div class="sub-merchant">{name}</div>
      <div class="sub-category">{info.get('category','Other')} · {info.get('frequency','?')} billing</div>
    </div>
  </div>
  <div style="text-align:right;white-space:nowrap;">
    <div class="sub-amount" style="color:#f5365c;">{amt_str}</div>
    {link_html}
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Renewals ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔔 Reminder Checklist</div>', unsafe_allow_html=True)
    renewals = report.get("upcoming_renewals_30d", [])
    if renewals:
        lines = [f"# Upcoming renewals — next 30 days", f"# Generated: {date.today().isoformat()}", ""]
        for r in renewals:
            lines.append(f"[ ] {r['renewal_date']}  {r['merchant']:30s}  {r['currency']} {r['amount']:,.2f}  (in {r['days_until']}d)")
        reminder_text = "\n".join(lines)
        st.code(reminder_text, language="text")
        st.download_button("Download renewals.txt", reminder_text, "upcoming_renewals.txt", "text/plain", key="dl_renewals")
    else:
        st.markdown('<p style="color:#8898aa;font-size:0.85rem;">No renewals predicted in the next 30 days.</p>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Quick-add + budget accessible via buttons ────────────────────────
    qa_l, qa_r = st.columns(2)
    with qa_l:
        if st.button("➕ Add subscription manually", key="btn_add_actions", type="secondary", use_container_width=True):
            dialog_add_subscription()
    with qa_r:
        if st.button("💰 Set monthly budget", key="btn_budget_actions", type="secondary", use_container_width=True):
            dialog_budget()

    # ── Alert Notifications ───────────────────────────────────────────────
    st.markdown('<div class="section-header">🔔 Alert Notifications</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8898aa;font-size:0.85rem;margin-bottom:1rem;">Get renewal reminders sent directly to your Telegram or WhatsApp.</p>', unsafe_allow_html=True)

    # Telegram
    st.markdown(
        '<div class="alert-card">'
        '<div class="alert-card-title">✈️ Telegram</div>'
        '<div class="alert-card-desc">Sends push notifications directly to your Telegram via a bot.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Set up Telegram alerts", expanded=bool(st.session_state.alert_telegram_token)):
        st.markdown(
            '<div class="alert-steps">'
            '1. Open Telegram → search <b>@BotFather</b> → /newbot → follow prompts<br>'
            '2. Copy the <b>Bot Token</b> (e.g. 123456:ABC-…)<br>'
            '3. Message <b>@userinfobot</b> to get your <b>Chat ID</b>'
            '</div>',
            unsafe_allow_html=True,
        )
        tg_token   = st.text_input("Bot Token", value=st.session_state.alert_telegram_token,   placeholder="123456789:AAFxxxxxx", key="input_tg_token")
        tg_chat_id = st.text_input("Chat ID",   value=st.session_state.alert_telegram_chat_id, placeholder="123456789",           key="input_tg_chat")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save Telegram", key="btn_save_tg"):
                st.session_state.alert_telegram_token   = tg_token
                st.session_state.alert_telegram_chat_id = tg_chat_id
                save_alert_config(tg_token, tg_chat_id, st.session_state.alert_whatsapp_number)
                st.success("Saved.")
        with c2:
            if st.button("Send Test Message", key="btn_test_tg"):
                if not tg_token or not tg_chat_id:
                    st.error("Fill in both fields first.")
                else:
                    ok, err = send_telegram_message(tg_token, tg_chat_id, "SubTrack ✅ — your alerts are working!")
                    st.success("Sent! Check Telegram.") if ok else st.error(f"Failed: {err}")
        if st.session_state.alert_telegram_token and st.session_state.alert_telegram_chat_id and report:
            if st.button("Send Renewal Alerts Now", key="btn_send_tg_alert"):
                ok, err = send_telegram_message(st.session_state.alert_telegram_token, st.session_state.alert_telegram_chat_id, build_renewal_alert_text(report))
                st.success("Alerts sent to Telegram!") if ok else st.error(f"Failed: {err}")

    # WhatsApp
    st.markdown(
        '<div class="alert-card">'
        '<div class="alert-card-title">💬 WhatsApp</div>'
        '<div class="alert-card-desc">Opens WhatsApp with a pre-filled renewal summary — works on any device.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Set up WhatsApp alerts", expanded=bool(st.session_state.alert_whatsapp_number)):
        st.markdown(
            '<div class="alert-steps">'
            '1. Enter your number with country code (e.g. +2348012345678)<br>'
            '2. Click <b>Open WhatsApp Alert</b> — opens WhatsApp with your summary pre-filled<br>'
            '3. Hit Send to deliver it to yourself'
            '</div>',
            unsafe_allow_html=True,
        )
        wa_number = st.text_input("WhatsApp number", value=st.session_state.alert_whatsapp_number, placeholder="+2348012345678", key="input_wa_number")
        if st.button("Save Number", key="btn_save_wa"):
            st.session_state.alert_whatsapp_number = wa_number
            save_alert_config(st.session_state.alert_telegram_token, st.session_state.alert_telegram_chat_id, wa_number)
            st.success("Saved.")
        if wa_number and report:
            msg_text  = build_renewal_alert_text(report).replace("*","").replace("_","")
            clean_num = wa_number.strip().replace(" ","").replace("+","")
            wa_url    = f"https://wa.me/{clean_num}?text={urllib.parse.quote(msg_text)}"
            st.markdown(
                f'<a href="{wa_url}" target="_blank" style="display:inline-block;margin-top:0.5rem;'
                'background:#25D366;color:#fff;padding:0.55rem 1.4rem;border-radius:8px;'
                'font-weight:600;font-size:0.88rem;text-decoration:none;'
                'box-shadow:0 4px 6px rgba(37,211,102,.3);">↗ Open WhatsApp Alert</a>',
                unsafe_allow_html=True,
            )

    # ── Background Scheduler ─────────────────────────────────────────────
    st.markdown('<div class="section-header">⏱ Background Scheduler</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8898aa;font-size:0.83rem;margin-bottom:0.75rem;">'
        'Two background jobs keep you informed without opening the app:<br>'
        '• <b>Weekly scan</b> — re-scans Gmail every Monday, sends a Telegram digest<br>'
        '• <b>Daily reminders</b> — checks every morning and sends an alert on the 3rd, 2nd and 1st day before each renewal</p>',
        unsafe_allow_html=True,
    )
    _cfg = {}
    if ALERT_CONFIG_FILE.exists():
        try: _cfg = json.loads(ALERT_CONFIG_FILE.read_text())
        except: pass
    last_scan    = _cfg.get("last_scan", "Never")
    _base        = Path(__file__).parent.resolve()
    _py          = str(_base / ".venv" / "bin" / "python")
    _sched       = str(_base / "scheduler.py")
    _wdir        = str(_base)
    _log         = str(_base / "scheduler.log")
    _weekly_lbl  = "com.subtrack.weekly"
    _remind_lbl  = "com.subtrack.remind"
    _weekly_path = Path.home() / "Library" / "LaunchAgents" / f"{_weekly_lbl}.plist"
    _remind_path = Path.home() / "Library" / "LaunchAgents" / f"{_remind_lbl}.plist"

    def _make_plist(label, extra_arg, hour):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array>
    <string>{_py}</string><string>{_sched}</string><string>{extra_arg}</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>0</integer>
  </dict>
  <key>WorkingDirectory</key><string>{_wdir}</string>
  <key>StandardOutPath</key><string>{_log}</string>
  <key>StandardErrorPath</key><string>{_log}</string>
  <key>RunAtLoad</key><false/>
</dict></plist>"""

    weekly_status = "✅ Installed" if _weekly_path.exists() else "Not installed"
    remind_status = "✅ Installed" if _remind_path.exists() else "Not installed"
    st.markdown(f"""
<div class="card" style="margin-bottom:0.75rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div><div style="font-size:0.85rem;font-weight:600;color:#32325d;">Last Gmail scan</div>
         <div style="font-size:0.78rem;color:#8898aa;">{last_scan}</div></div>
    <div style="text-align:right">
      <div style="font-size:0.75rem;color:#8898aa;">Weekly · {weekly_status}</div>
      <div style="font-size:0.75rem;color:#8898aa;">Daily reminders · {remind_status}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    with st.expander("Set up background jobs (macOS)", expanded=not (_weekly_path.exists() and _remind_path.exists())):
        st.markdown(
            '<div class="alert-steps">'
            '1. Download both plist files below<br>'
            '2. Move them to <b>~/Library/LaunchAgents/</b><br>'
            f'3. Load each one in Terminal:<br>'
            f'&nbsp;&nbsp;<code>launchctl load ~/Library/LaunchAgents/{_weekly_lbl}.plist</code><br>'
            f'&nbsp;&nbsp;<code>launchctl load ~/Library/LaunchAgents/{_remind_lbl}.plist</code><br>'
            '4. Done — weekly scans and daily reminders run automatically'
            '</div>',
            unsafe_allow_html=True,
        )
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button("⬇ Weekly scan plist",     _make_plist(_weekly_lbl, "--once",    8), f"{_weekly_lbl}.plist",  "application/xml", key="dl_weekly_plist")
        with dl2:
            st.download_button("⬇ Daily reminders plist", _make_plist(_remind_lbl, "--remind",  9), f"{_remind_lbl}.plist",  "application/xml", key="dl_remind_plist")
        st.markdown(
            '<div class="alert-steps" style="margin-top:0.5rem;">'
            'Run manually from Terminal anytime:<br>'
            '<code>python scheduler.py --once</code> &nbsp;(full scan)<br>'
            '<code>python scheduler.py --remind</code> &nbsp;(reminders only)'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back to Results", type="secondary", use_container_width=True):
        go_to(3); st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────
# Load saved credentials + alert config on every run (so fields auto-fill)
load_saved_credentials()
load_alert_config()

# Fire 1/2/3-day renewal reminders if a report is already available
if st.session_state.report:
    n = check_and_send_renewal_reminders(st.session_state.report)
    if n:
        st.toast(f"Sent {n} renewal reminder{'s' if n != 1 else ''} via Telegram!", icon="⏰")

render_header()
render_step_bar(st.session_state.step)

if   st.session_state.step == 1: render_connect()
elif st.session_state.step == 2: render_scanning()
elif st.session_state.step == 3: render_results()
elif st.session_state.step == 4: render_actions()
