from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any
import json
import os
import threading
import time
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
import parser
import analyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("api")

app = FastAPI(title="SubTrack API")

# ── Simple shared-password auth ───────────────────────────────────────────────
# Set ACCESS_PASSWORD env var, or it defaults to "subtrack" for local dev
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "subtrack")
ACTIVE_TOKENS: set = set()


class LoginRequest(BaseModel):
    password: str


@app.post("/auth/login")
def auth_login(req: LoginRequest):
    if req.password == ACCESS_PASSWORD:
        token = secrets.token_urlsafe(32)
        ACTIVE_TOKENS.add(token)
        return {"status": "success", "token": token}
    return {"status": "error", "message": "Wrong password."}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Allow: auth endpoints, static files, root
    if (path.startswith("/auth/") or
        path.startswith("/assets/") or
        path == "/" or
        path == "/favicon.ico" or
        path.endswith(".js") or
        path.endswith(".css") or
        path.endswith(".html") or
        path.endswith(".svg") or
        path.endswith(".png") or
        path.endswith(".ico")):
        return await call_next(request)

    # All /api/* routes require auth token
    if path.startswith("/api/"):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token not in ACTIVE_TOKENS:
            return Response(content='{"error":"unauthorized"}', status_code=401,
                           media_type="application/json")
    return await call_next(request)

# Allow requests from the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config helpers ────────────────────────────────────────────────────────────
ALERT_CONFIG_FILE = Path("alerts_config.json")
SENT_ALERTS_FILE  = Path("sent_alerts.json")
REMINDER_DAYS     = [3, 2, 1]
CURRENCY_SYMBOLS  = {"USD": "$", "NGN": "₦", "GBP": "£", "EUR": "€"}


def load_config() -> dict:
    if ALERT_CONFIG_FILE.exists():
        try:
            return json.loads(ALERT_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    ALERT_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(token: str, chat_id: str, text: str) -> bool:
    import urllib.request
    try:
        url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
        payload = json.dumps({"chat_id": chat_id.strip(), "text": text, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as exc:
        log.warning(f"Telegram send failed: {exc}")
        return False


def build_scan_summary(report: dict) -> str:
    """Build a Telegram-friendly scan summary message."""
    lines = ["*SubTrack — Scan Complete* 📊\n"]
    count = report.get("merchant_count", 0)
    spend = report.get("spend_by_currency", {})

    lines.append(f"👀 *{count}* active subscription{'s' if count != 1 else ''}")
    if spend:
        lines.append("💳 Monthly: *" + " · ".join(
            f"{CURRENCY_SYMBOLS.get(c, c)}{a:,.2f}" for c, a in spend.items()
        ) + "*")

    for m in report.get("merchants", []):
        sym = CURRENCY_SYMBOLS.get(m["currency"], m["currency"] + " ")
        lines.append(f"• {m['merchant']} — {sym}{m['monthly_cost']:,.2f}/mo")

    renewals = report.get("upcoming_renewals_30d", [])
    if renewals:
        lines.append("\n*⏰ Upcoming renewals (30 days):*")
        for r in renewals:
            sym = CURRENCY_SYMBOLS.get(r["currency"], r["currency"] + " ")
            lines.append(f"• *{r['merchant']}* — {sym}{r['amount']:,.2f} in {r['days_until']}d ({r['renewal_date']})")
    else:
        lines.append("\n✅ No renewals due in the next 30 days")

    return "\n".join(lines)


def fire_renewal_reminders(report: dict, token: str, chat_id: str) -> int:
    """Send Telegram reminders for renewals 3, 2, or 1 day(s) away (deduped)."""
    from datetime import date
    renewals = report.get("upcoming_renewals_30d", [])
    today = date.today()

    sent: dict = {}
    if SENT_ALERTS_FILE.exists():
        try:
            sent = json.loads(SENT_ALERTS_FILE.read_text())
        except Exception:
            pass

    count = 0
    for r in renewals:
        days = r.get("days_until", 999)
        if days not in REMINDER_DAYS:
            continue
        key = f"{r['renewal_date']}_{r['merchant']}_{days}"
        if key in sent:
            continue
        day_word = "day" if days == 1 else "days"
        sym = CURRENCY_SYMBOLS.get(r["currency"], r["currency"] + " ")
        msg = (
            f"⏰ *Renewal Reminder — SubTrack*\n\n"
            f"*{r['merchant']}* renews in *{days} {day_word}* ({r['renewal_date']}).\n"
            f"Amount: *{sym}{r['amount']:,.2f}*\n\n"
            f"If you don\u2019t wish to continue, cancel now."
        )
        if send_telegram(token, chat_id, msg):
            sent[key] = today.isoformat()
            count += 1
            log.info(f"Reminder sent: {r['merchant']} in {days}d")

    if count:
        SENT_ALERTS_FILE.write_text(json.dumps(sent, indent=2))
    return count


# ── Scan state ────────────────────────────────────────────────────────────────
class Credentials(BaseModel):
    email: str
    password: str


scan_state = {
    "is_running": False,
    "total": 100,
    "current": 0,
    "recent_log": "",
    "error": None,
    "done": False,
}


def scan_worker(email: str, password: str):
    global scan_state
    scan_state["is_running"] = True
    scan_state["done"] = False
    scan_state["error"] = None

    def progress_callback(current, total, record):
        scan_state["current"] = current
        scan_state["total"] = max(total, 1)
        if record:
            merchant = record.get("merchant", "Unknown")
            scan_state["recent_log"] = f"Processed {merchant}..."

    try:
        # 1. Run the parser
        scan_state["recent_log"] = "Connecting to IMAP server..."
        parser.run_parser(email, password, progress_callback=progress_callback)

        # 2. Run the analyzer
        scan_state["recent_log"] = "Analyzing results..."
        report_data = analyzer.run_analysis()
        with open("report.json", "w") as f:
            json.dump(report_data, f)

        scan_state["done"] = True

        # 3. Send Telegram summary after scan
        cfg = load_config()
        tg_token = cfg.get("telegram_token", "").strip()
        tg_chat_id = cfg.get("telegram_chat_id", "").strip()
        if tg_token and tg_chat_id:
            summary = build_scan_summary(report_data)
            send_telegram(tg_token, tg_chat_id, summary)
            log.info("Telegram scan summary sent.")

            # Also check for renewal reminders
            reminded = fire_renewal_reminders(report_data, tg_token, tg_chat_id)
            if reminded:
                log.info(f"Sent {reminded} renewal reminder(s).")

        # Update last_scan timestamp
        cfg["last_scan"] = datetime.now(timezone.utc).isoformat()
        save_config(cfg)

    except Exception as e:
        scan_state["error"] = str(e)
    finally:
        scan_state["is_running"] = False


# ── Scheduled background jobs ─────────────────────────────────────────────────
def scheduled_weekly_scan():
    """Run a full scan using saved credentials — called by the scheduler."""
    cfg = load_config()
    email = cfg.get("email_addr", "").strip()
    password = cfg.get("app_password", "").strip()
    if not email or not password:
        log.warning("Scheduled scan skipped — no saved credentials.")
        return
    log.info("Starting scheduled weekly scan...")
    scan_worker(email, password)


def scheduled_daily_reminders():
    """Check for renewal reminders using the latest report — no Gmail scan."""
    cfg = load_config()
    tg_token = cfg.get("telegram_token", "").strip()
    tg_chat_id = cfg.get("telegram_chat_id", "").strip()
    if not tg_token or not tg_chat_id:
        log.warning("Reminder check skipped — no Telegram credentials.")
        return

    report = analyzer.run_analysis()
    reminded = fire_renewal_reminders(report, tg_token, tg_chat_id)
    log.info(f"Daily reminder check: {reminded} reminder(s) sent.")


def run_scheduler():
    """Background thread: weekly scan (Mondays 08:00) + daily reminders (09:00)."""
    import schedule

    schedule.every().monday.at("08:00").do(scheduled_weekly_scan)
    schedule.every().day.at("09:00").do(scheduled_daily_reminders)

    log.info("Scheduler started — weekly scan Mon 08:00, daily reminders 09:00")

    # Fire reminders immediately on startup if a report exists
    if os.path.exists("report.json"):
        try:
            scheduled_daily_reminders()
        except Exception as exc:
            log.warning(f"Startup reminder check failed: {exc}")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ── API routes ────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """Start the scheduler thread when the API server boots."""
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    log.info("Background scheduler thread launched.")


@app.get("/api/report")
def get_report() -> Dict[str, Any]:
    try:
        if not os.path.exists("report.json"):
            return {"error": "Report not found. Please run the parser first."}
        with open("report.json", "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connect")
def connect_email(creds: Credentials):
    global scan_state
    if scan_state["is_running"]:
        return {"status": "error", "message": "A scan is already running."}

    # Save credentials for scheduled scans
    cfg = load_config()
    cfg["email_addr"] = creds.email
    cfg["app_password"] = creds.password
    save_config(cfg)

    # Start the background worker
    threading.Thread(target=scan_worker, args=(creds.email, creds.password), daemon=True).start()
    return {"status": "success", "message": "Scan started."}


@app.get("/api/progress")
def get_progress():
    global scan_state
    if scan_state["error"]:
        return {"status": "error", "message": scan_state["error"]}
    if scan_state["done"]:
        return {"status": "done"}

    return {
        "status": "scanning",
        "processed": scan_state["current"],
        "total": scan_state["total"],
        "recent_log": scan_state["recent_log"],
    }


@app.post("/api/cancel")
def cancel_scan():
    return {"status": "success"}


# ── Manual subscription entry ─────────────────────────────────────────────────
class ManualSubscription(BaseModel):
    merchant: str
    amount: float
    currency: str = "USD"
    frequency: str = "monthly"
    date: str = ""  # ISO date string


@app.post("/api/subscriptions/add")
def add_subscription(sub: ManualSubscription):
    """Add a manual subscription to subscriptions.jsonl and re-run analysis."""
    import hashlib
    if not sub.merchant.strip():
        return {"status": "error", "message": "Service name is required."}

    use_date = sub.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    record = {
        "id": hashlib.sha256(f"manual:{sub.merchant}:{sub.amount}:{use_date}".encode()).hexdigest()[:16],
        "merchant": sub.merchant.strip(),
        "amount": round(sub.amount, 2),
        "currency": sub.currency,
        "date": use_date,
        "subject": f"Manual entry: {sub.merchant.strip()}",
        "source_email": "manual",
        "detected_keywords": [],
        "status": "active",
        "source": "manual",
        "frequency_override": sub.frequency,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
    }
    with open("subscriptions.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")

    # Re-run analysis and update report
    report_data = analyzer.run_analysis()
    with open("report.json", "w") as f:
        json.dump(report_data, f)

    return {
        "status": "success",
        "message": f"Added {sub.merchant.strip()} ({sub.currency} {sub.amount:,.2f}/{sub.frequency}).",
    }


# ── Cancellation links ────────────────────────────────────────────────────────
CANCELLATION_LINKS = {
    "netflix": "https://www.netflix.com/cancel",
    "spotify": "https://www.spotify.com/account/subscription/",
    "hulu": "https://secure.hulu.com/account/cancel",
    "disney": "https://www.disneyplus.com/account",
    "hbo": "https://www.max.com/account",
    "max": "https://www.max.com/account",
    "peacock": "https://www.peacocktv.com/account",
    "paramount": "https://www.paramountplus.com/account/",
    "apple tv": "https://support.apple.com/en-us/118428",
    "apple music": "https://support.apple.com/en-us/118428",
    "apple": "https://appleid.apple.com/account/manage",
    "youtube": "https://youtube.com/paid_memberships",
    "amazon": "https://www.amazon.com/mc/pipelines/cancellation",
    "tidal": "https://listen.tidal.com/account/subscription",
    "deezer": "https://www.deezer.com/en/account/premium-subscription",
    "openai": "https://platform.openai.com/account/billing",
    "anthropic": "https://console.anthropic.com/settings/billing",
    "claude": "https://console.anthropic.com/settings/billing",
    "gemini": "https://one.google.com/about",
    "midjourney": "https://www.midjourney.com/account/",
    "perplexity": "https://www.perplexity.ai/settings",
    "grammarly": "https://account.grammarly.com/subscription",
    "notion": "https://www.notion.so/profile/plans",
    "github": "https://github.com/settings/billing",
    "gitlab": "https://gitlab.com/-/profile/billing",
    "jira": "https://admin.atlassian.com/",
    "confluence": "https://admin.atlassian.com/",
    "asana": "https://app.asana.com/-/account_api",
    "trello": "https://trello.com/billing",
    "monday": "https://auth.monday.com/login",
    "linear": "https://linear.app/settings/subscription",
    "dropbox": "https://www.dropbox.com/account/plan",
    "google one": "https://one.google.com/about",
    "adobe": "https://account.adobe.com/plans",
    "figma": "https://www.figma.com/settings",
    "canva": "https://www.canva.com/settings/plans-and-billing",
    "zoom": "https://zoom.us/billing",
    "slack": "https://slack.com/intl/en-us/help/articles/204369004",
    "nordvpn": "https://my.nordaccount.com/subscription/",
    "expressvpn": "https://www.expressvpn.com/subscriptions",
    "surfshark": "https://my.surfshark.com/subscriptions",
    "1password": "https://my.1password.com/profile",
    "lastpass": "https://lastpass.com/",
    "dashlane": "https://app.dashlane.com/login",
    "bitwarden": "https://vault.bitwarden.com/",
    "shopify": "https://admin.shopify.com/settings/billing",
    "squarespace": "https://account.squarespace.com/subscriptions",
    "wordpress": "https://wordpress.com/purchases",
    "webflow": "https://webflow.com/account",
    "wix": "https://manage.wix.com/premium-purchase-plan/dynamo",
    "duolingo": "https://www.duolingo.com/settings",
    "coursera": "https://www.coursera.org/account-profile#subscriptions",
    "udemy": "https://www.udemy.com/dashboard/subscription",
    "masterclass": "https://www.masterclass.com/account/subscription",
    "linkedin": "https://www.linkedin.com/premium/manage/cancel",
    "nytimes": "https://www.nytimes.com/subscription",
    "medium": "https://medium.com/me/membership",
    "substack": "https://substack.com/settings",
    "bloomberg": "https://www.bloomberg.com/account/",
    "xero": "https://go.xero.com/Settings/Subscription",
    "quickbooks": "https://accounts.intuit.com/",
    "vercel": "https://vercel.com/account/billing",
    "netlify": "https://app.netlify.com/teams/user/billing/subscriptions",
    "digitalocean": "https://cloud.digitalocean.com/account/billing",
    "heroku": "https://dashboard.heroku.com/account/billing",
    "starlink": "https://www.starlink.com/account",
    "microsoft": "https://account.microsoft.com/services/",
    "google": "https://myaccount.google.com/payments-and-subscriptions",
    "patreon": "https://www.patreon.com/settings/memberships",
    "twitch": "https://www.twitch.tv/settings/prime",
    "loom": "https://www.loom.com/account",
}


def get_cancellation_link(merchant: str) -> str:
    lower = merchant.lower()
    best_kw, best_url = "", ""
    for kw, url in CANCELLATION_LINKS.items():
        if kw in lower and len(kw) > len(best_kw):
            best_kw, best_url = kw, url
    return best_url


# Persistent set of merchants marked for cancellation
_marked_for_cancellation: set = set()


@app.get("/api/cancellation")
def get_cancellation_info():
    """Return cancellation links and marked subscriptions."""
    report = {}
    if os.path.exists("report.json"):
        with open("report.json") as f:
            report = json.load(f)

    merchants = report.get("merchants", [])
    result = []
    for m in merchants:
        cancel_url = get_cancellation_link(m["merchant"])
        result.append({
            "merchant": m["merchant"],
            "category": m.get("category", "Other"),
            "currency": m.get("currency", "USD"),
            "monthly_cost": m.get("monthly_cost", 0),
            "frequency": m.get("frequency", "monthly"),
            "cancel_url": cancel_url or f"https://www.google.com/search?q={m['merchant']}+cancel+subscription",
            "has_direct_link": bool(cancel_url),
            "marked": m["merchant"] in _marked_for_cancellation,
        })
    return {"subscriptions": result, "marked_count": len(_marked_for_cancellation)}


class MarkCancellation(BaseModel):
    merchant: str
    mark: bool


@app.post("/api/cancellation/mark")
def mark_for_cancellation(data: MarkCancellation):
    """Toggle mark/unmark a subscription for cancellation."""
    if data.mark:
        _marked_for_cancellation.add(data.merchant)
    else:
        _marked_for_cancellation.discard(data.merchant)
    return {"status": "success", "marked": list(_marked_for_cancellation)}


# ── Health score ──────────────────────────────────────────────────────────────
@app.get("/api/health-score")
def get_health_scores():
    """Compute a health score for each subscription based on usage signals."""
    report = {}
    if os.path.exists("report.json"):
        with open("report.json") as f:
            report = json.load(f)

    from datetime import date as date_type
    today = date_type.today()
    results = []

    for m in report.get("merchants", []):
        score = 50  # Base score
        label = "Fair"
        tips = []

        # Factor 1: Charge frequency — more charges = more active
        charges = m.get("charge_count", 1)
        if charges >= 6:
            score += 20
        elif charges >= 3:
            score += 10

        # Factor 2: Recency — how recently was the last charge?
        last_charge = m.get("last_charge", "")
        if last_charge:
            try:
                last_dt = date_type.fromisoformat(last_charge)
                days_ago = (today - last_dt).days
                if days_ago <= 30:
                    score += 20
                elif days_ago <= 60:
                    score += 10
                elif days_ago > 90:
                    score -= 15
                    tips.append(f"No charge in {days_ago} days — might be forgotten")
            except ValueError:
                pass

        # Factor 3: Is it marked as forgotten by the analyzer?
        if m.get("is_forgotten"):
            score -= 20
            tips.append("Flagged as potentially forgotten")

        # Factor 4: Cost relative to total
        cost = m.get("monthly_cost", 0)
        if cost > 50:
            tips.append("High-cost subscription — verify it's worth it")
        elif cost < 5:
            score += 5  # Low cost = less risky

        # Factor 5: Overlaps
        overlaps = report.get("overlaps", [])
        for ov in overlaps:
            if m["merchant"] in (ov.get("merchant_a"), ov.get("merchant_b")):
                score -= 15
                tips.append(f"Overlaps with another service in '{ov['category']}'")
                break

        # Clamp and label
        score = max(0, min(100, score))
        if score >= 75:
            label = "Healthy"
        elif score >= 50:
            label = "Fair"
        elif score >= 25:
            label = "Review"
        else:
            label = "Cancel?"

        sym = CURRENCY_SYMBOLS.get(m.get("currency", "USD"), "$")
        results.append({
            "merchant": m["merchant"],
            "category": m.get("category", "Other"),
            "currency": m.get("currency", "USD"),
            "monthly_cost": m.get("monthly_cost", 0),
            "score": score,
            "label": label,
            "tips": tips,
            "charge_count": charges,
            "last_charge": last_charge,
        })

    # Sort worst scores first
    results.sort(key=lambda x: x["score"])
    return {"subscriptions": results}


@app.get("/api/alerts/config")
def get_alerts_config():
    """Return the current alert configuration (tokens censored)."""
    cfg = load_config()
    return {
        "telegram_configured": bool(cfg.get("telegram_token", "").strip()),
        "telegram_chat_id": cfg.get("telegram_chat_id", ""),
        "whatsapp_number": cfg.get("whatsapp_number", ""),
        "last_scan": cfg.get("last_scan", "Never"),
    }


class AlertConfig(BaseModel):
    telegram_token: str = ""
    telegram_chat_id: str = ""
    whatsapp_number: str = ""


@app.post("/api/alerts/config")
def update_alerts_config(config: AlertConfig):
    """Update Telegram and WhatsApp alert configuration."""
    cfg = load_config()
    if config.telegram_token.strip():
        cfg["telegram_token"] = config.telegram_token.strip()
    if config.telegram_chat_id.strip():
        cfg["telegram_chat_id"] = config.telegram_chat_id.strip()
    cfg["whatsapp_number"] = config.whatsapp_number.strip()
    save_config(cfg)
    return {"status": "success", "message": "Alert configuration saved."}


@app.post("/api/alerts/test")
def test_telegram_alert():
    """Send a test Telegram message."""
    cfg = load_config()
    token = cfg.get("telegram_token", "").strip()
    chat_id = cfg.get("telegram_chat_id", "").strip()
    if not token or not chat_id:
        return {"status": "error", "message": "No Telegram credentials configured."}

    ok = send_telegram(token, chat_id, "✅ *SubTrack* — Test message received! Alerts are working.")
    if ok:
        return {"status": "success", "message": "Test message sent!"}
    return {"status": "error", "message": "Failed to send. Check your token and chat ID."}


@app.get("/api/scheduler/status")
def scheduler_status():
    """Return scheduler status information."""
    cfg = load_config()
    return {
        "last_scan": cfg.get("last_scan", "Never"),
        "weekly_scan": "Mondays 08:00",
        "daily_reminders": "Daily 09:00",
        "telegram_configured": bool(cfg.get("telegram_token", "").strip()),
        "credentials_saved": bool(cfg.get("email_addr", "").strip()),
    }


# ── Serve React frontend build ────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    log.warning("Frontend build not found at %s. Run 'npm run build' in frontend/", FRONTEND_DIR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
