from fastapi import FastAPI, HTTPException, Request, Response, Depends
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
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
import parser
import analyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("api")

app = FastAPI(title="SubTrack API")

# ── Auth ───────────────────────────────────────────────────────────────────────
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "subtrack")
# token → email (empty string until the user calls /api/connect)
ACTIVE_TOKENS: Dict[str, str] = {}


class LoginRequest(BaseModel):
    password: str


class Credentials(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def auth_login(req: LoginRequest):
    if req.password == ACCESS_PASSWORD:
        token = secrets.token_urlsafe(32)
        ACTIVE_TOKENS[token] = ""
        return {"status": "success", "token": token}
    return {"status": "error", "message": "Wrong password."}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
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

    if path.startswith("/api/"):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token not in ACTIVE_TOKENS:
            return Response(content='{"error":"unauthorized"}', status_code=401,
                            media_type="application/json")
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Per-user data isolation ────────────────────────────────────────────────────

def user_dir(email: str) -> Path:
    """Return (and create) an isolated data directory for this email."""
    safe = hashlib.md5(email.lower().strip().encode()).hexdigest()[:16]
    d = Path("data") / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def current_email(request: Request) -> str:
    """Extract the email associated with the bearer token."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return ACTIVE_TOKENS.get(token, "")


# ── Config helpers (per-user) ──────────────────────────────────────────────────
REMINDER_DAYS = [3, 2, 1]
CURRENCY_SYMBOLS = {"USD": "$", "NGN": "₦", "GBP": "£", "EUR": "€"}


def load_config(email: str) -> dict:
    cfg_file = user_dir(email) / "alerts_config.json"
    if cfg_file.exists():
        try:
            return json.loads(cfg_file.read_text())
        except Exception:
            pass
    return {}


def save_config(email: str, cfg: dict):
    (user_dir(email) / "alerts_config.json").write_text(json.dumps(cfg, indent=2))


# ── Telegram ───────────────────────────────────────────────────────────────────
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


def fire_renewal_reminders(report: dict, email: str, tg_token: str, chat_id: str) -> int:
    from datetime import date
    renewals = report.get("upcoming_renewals_30d", [])
    today = date.today()
    sent_file = user_dir(email) / "sent_alerts.json"
    sent: dict = {}
    if sent_file.exists():
        try:
            sent = json.loads(sent_file.read_text())
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
        if send_telegram(tg_token, chat_id, msg):
            sent[key] = today.isoformat()
            count += 1
    if count:
        sent_file.write_text(json.dumps(sent, indent=2))
    return count


# ── Per-user scan state ────────────────────────────────────────────────────────
# email → state dict
scan_states: Dict[str, dict] = {}

def get_scan_state(email: str) -> dict:
    if email not in scan_states:
        scan_states[email] = {
            "is_running": False, "total": 100, "current": 0,
            "recent_log": "", "error": None, "done": False,
        }
    return scan_states[email]


def scan_worker(email: str, password: str):
    state = get_scan_state(email)
    state.update({"is_running": True, "done": False, "error": None})
    udir = user_dir(email)

    def progress_callback(current, total, record):
        state["current"] = current
        state["total"] = max(total, 1)
        if record:
            state["recent_log"] = f"Processed {record.get('merchant', 'Unknown')}..."

    try:
        state["recent_log"] = "Connecting to IMAP server..."
        parser.run_parser(email, password,
                          progress_callback=progress_callback,
                          output_file=str(udir / "subscriptions.jsonl"))

        state["recent_log"] = "Analyzing results..."
        report_data = analyzer.run_analysis(filepath=udir / "subscriptions.jsonl")
        (udir / "report.json").write_text(json.dumps(report_data))

        state["done"] = True

        cfg = load_config(email)
        tg_token = cfg.get("telegram_token", "").strip()
        tg_chat_id = cfg.get("telegram_chat_id", "").strip()
        if tg_token and tg_chat_id:
            send_telegram(tg_token, tg_chat_id, build_scan_summary(report_data))
            fire_renewal_reminders(report_data, email, tg_token, tg_chat_id)

        cfg["last_scan"] = datetime.now(timezone.utc).isoformat()
        save_config(email, cfg)

    except Exception as e:
        state["error"] = str(e)
        log.error(f"Scan error for {email}: {e}")
    finally:
        state["is_running"] = False


# ── Per-user cancellation marks ────────────────────────────────────────────────
marked_per_user: Dict[str, set] = {}

def get_marked(email: str) -> set:
    if email not in marked_per_user:
        marked_per_user[email] = set()
    return marked_per_user[email]


# ── Scheduled background jobs ──────────────────────────────────────────────────
def run_scheduler():
    import schedule

    def daily_reminders_all_users():
        for email_hash_dir in Path("data").iterdir():
            cfg_file = email_hash_dir / "alerts_config.json"
            report_file = email_hash_dir / "report.json"
            if not cfg_file.exists() or not report_file.exists():
                continue
            try:
                cfg = json.loads(cfg_file.read_text())
                tg_token = cfg.get("telegram_token", "").strip()
                tg_chat_id = cfg.get("telegram_chat_id", "").strip()
                email = cfg.get("email_addr", "").strip()
                if not tg_token or not tg_chat_id or not email:
                    continue
                report = json.loads(report_file.read_text())
                fire_renewal_reminders(report, email, tg_token, tg_chat_id)
            except Exception as exc:
                log.warning(f"Reminder check failed for {email_hash_dir.name}: {exc}")

    schedule.every().day.at("09:00").do(daily_reminders_all_users)
    log.info("Scheduler started — daily reminders at 09:00 for all users")

    while True:
        schedule.run_pending()
        time.sleep(30)


@app.on_event("startup")
def on_startup():
    Path("data").mkdir(exist_ok=True)
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()


# ── API routes ─────────────────────────────────────────────────────────────────
@app.post("/api/connect")
def connect_email(creds: "Credentials", request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token in ACTIVE_TOKENS:
        ACTIVE_TOKENS[token] = creds.email  # bind email to this session token

    state = get_scan_state(creds.email)
    if state["is_running"]:
        return {"status": "error", "message": "A scan is already running."}

    cfg = load_config(creds.email)
    cfg["email_addr"] = creds.email
    cfg["app_password"] = creds.password
    save_config(creds.email, cfg)

    threading.Thread(target=scan_worker, args=(creds.email, creds.password), daemon=True).start()
    return {"status": "success", "message": "Scan started."}


@app.get("/api/progress")
def get_progress(request: Request):
    email = current_email(request)
    state = get_scan_state(email)
    if state["error"]:
        return {"status": "error", "message": state["error"]}
    if state["done"]:
        return {"status": "done"}
    return {
        "status": "scanning",
        "processed": state["current"],
        "total": state["total"],
        "recent_log": state["recent_log"],
    }


@app.post("/api/cancel")
def cancel_scan():
    return {"status": "success"}


@app.get("/api/report")
def get_report(request: Request):
    email = current_email(request)
    report_file = user_dir(email) / "report.json"
    if not report_file.exists():
        return {"error": "No report found. Please run the scanner first."}
    try:
        return json.loads(report_file.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ManualSubscription(BaseModel):
    merchant: str
    amount: float
    currency: str = "USD"
    frequency: str = "monthly"
    date: str = ""


@app.post("/api/subscriptions/add")
def add_subscription(sub: ManualSubscription, request: Request):
    email = current_email(request)
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
    udir = user_dir(email)
    with open(udir / "subscriptions.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")

    report_data = analyzer.run_analysis(filepath=udir / "subscriptions.jsonl")
    (udir / "report.json").write_text(json.dumps(report_data))

    return {
        "status": "success",
        "message": f"Added {sub.merchant.strip()} ({sub.currency} {sub.amount:,.2f}/{sub.frequency}).",
    }


# ── Cancellation links ─────────────────────────────────────────────────────────
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


@app.get("/api/cancellation")
def get_cancellation_info(request: Request):
    email = current_email(request)
    report_file = user_dir(email) / "report.json"
    report = json.loads(report_file.read_text()) if report_file.exists() else {}
    marked = get_marked(email)
    result = []
    for m in report.get("merchants", []):
        cancel_url = get_cancellation_link(m["merchant"])
        result.append({
            "merchant": m["merchant"],
            "category": m.get("category", "Other"),
            "currency": m.get("currency", "USD"),
            "monthly_cost": m.get("monthly_cost", 0),
            "frequency": m.get("frequency", "monthly"),
            "cancel_url": cancel_url or f"https://www.google.com/search?q={m['merchant']}+cancel+subscription",
            "has_direct_link": bool(cancel_url),
            "marked": m["merchant"] in marked,
        })
    return {"subscriptions": result, "marked_count": len(marked)}


class MarkCancellation(BaseModel):
    merchant: str
    mark: bool


@app.post("/api/cancellation/mark")
def mark_for_cancellation(data: MarkCancellation, request: Request):
    email = current_email(request)
    marked = get_marked(email)
    if data.mark:
        marked.add(data.merchant)
    else:
        marked.discard(data.merchant)
    return {"status": "success", "marked": list(marked)}


@app.get("/api/health-score")
def get_health_scores(request: Request):
    email = current_email(request)
    report_file = user_dir(email) / "report.json"
    report = json.loads(report_file.read_text()) if report_file.exists() else {}

    from datetime import date as date_type
    today = date_type.today()
    results = []

    for m in report.get("merchants", []):
        score = 50
        tips = []
        charges = m.get("charge_count", 1)
        if charges >= 6:
            score += 20
        elif charges >= 3:
            score += 10

        last_charge = m.get("last_charge", "")
        if last_charge:
            try:
                days_ago = (today - date_type.fromisoformat(last_charge)).days
                if days_ago <= 30:
                    score += 20
                elif days_ago <= 60:
                    score += 10
                elif days_ago > 90:
                    score -= 15
                    tips.append(f"No charge in {days_ago} days — might be forgotten")
            except ValueError:
                pass

        if m.get("is_forgotten"):
            score -= 20
            tips.append("Flagged as potentially forgotten")

        cost = m.get("monthly_cost", 0)
        if cost > 50:
            tips.append("High-cost subscription — verify it's worth it")
        elif cost < 5:
            score += 5

        for ov in report.get("overlaps", []):
            if m["merchant"] in (ov.get("merchant_a"), ov.get("merchant_b")):
                score -= 15
                tips.append(f"Overlaps with another service in '{ov['category']}'")
                break

        score = max(0, min(100, score))
        label = "Healthy" if score >= 75 else "Fair" if score >= 50 else "Review" if score >= 25 else "Cancel?"
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

    results.sort(key=lambda x: x["score"])
    return {"subscriptions": results}


@app.get("/api/alerts/config")
def get_alerts_config(request: Request):
    email = current_email(request)
    cfg = load_config(email)
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
def update_alerts_config(config: AlertConfig, request: Request):
    email = current_email(request)
    cfg = load_config(email)
    if config.telegram_token.strip():
        cfg["telegram_token"] = config.telegram_token.strip()
    if config.telegram_chat_id.strip():
        cfg["telegram_chat_id"] = config.telegram_chat_id.strip()
    cfg["whatsapp_number"] = config.whatsapp_number.strip()
    save_config(email, cfg)
    return {"status": "success", "message": "Alert configuration saved."}


@app.post("/api/alerts/test")
def test_telegram_alert(request: Request):
    email = current_email(request)
    cfg = load_config(email)
    token = cfg.get("telegram_token", "").strip()
    chat_id = cfg.get("telegram_chat_id", "").strip()
    if not token or not chat_id:
        return {"status": "error", "message": "No Telegram credentials configured."}
    ok = send_telegram(token, chat_id, "✅ *SubTrack* — Test message received!")
    return {"status": "success" if ok else "error",
            "message": "Test message sent!" if ok else "Failed. Check token and chat ID."}


@app.get("/api/scheduler/status")
def scheduler_status(request: Request):
    email = current_email(request)
    cfg = load_config(email)
    return {
        "last_scan": cfg.get("last_scan", "Never"),
        "weekly_scan": "Mondays 08:00",
        "daily_reminders": "Daily 09:00",
        "telegram_configured": bool(cfg.get("telegram_token", "").strip()),
        "credentials_saved": bool(cfg.get("email_addr", "").strip()),
    }


# ── Serve React frontend ───────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    log.warning("Frontend build not found at %s. Run 'npm run build' in frontend/", FRONTEND_DIR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
