"""
scheduler.py — SubTrack Scheduler

Two operating modes:
  --remind   Check existing report for 3/2/1-day renewal reminders only (no Gmail scan).
             Run this DAILY so you never miss a reminder.
  (default)  Full Gmail scan + analysis + Telegram digest.
             Run this WEEKLY — scanning every day is overkill.

Recommended setup (two launchd plists):
  1. Weekly scan   → every Monday 08:00  → python scheduler.py
  2. Daily remind  → every day  09:00  → python scheduler.py --remind

Usage:
    python scheduler.py           # run full scan now, then weekly on Mondays 08:00
    python scheduler.py --remind  # check reminders now, then daily at 09:00
    python scheduler.py --once    # full scan once, then exit
"""

import json
import logging
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import schedule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ALERT_CONFIG_FILE = Path("alerts_config.json")
SENT_ALERTS_FILE  = Path("sent_alerts.json")
REMINDER_DAYS     = [3, 2, 1]
CURRENCY_SYMBOLS  = {"USD": "$", "NGN": "₦", "GBP": "£", "EUR": "€"}


# ── Config helpers ─────────────────────────────────────────────────────────────
def load_config() -> dict:
    if ALERT_CONFIG_FILE.exists():
        try:
            return json.loads(ALERT_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}

def save_config(cfg: dict):
    ALERT_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


# ── Telegram ───────────────────────────────────────────────────────────────────
def send_telegram(token: str, chat_id: str, text: str) -> bool:
    try:
        token = token.strip(); chat_id = chat_id.strip()
        url     = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
        req     = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as exc:
        log.warning(f"Telegram send failed: {exc}")
        return False


# ── Renewal reminders (fires every day it's run; dedup via sent_alerts.json) ──
def fire_renewal_reminders(report: dict, token: str, chat_id: str) -> int:
    """
    Send a Telegram message for each renewal that is exactly 3, 2, or 1 day(s)
    away. Deduplication key = renewal_date + merchant + days_until, so each
    (merchant, distance) pair is only messaged once per day.
    """
    renewals = report.get("upcoming_renewals_30d", [])
    today    = date.today()
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
            f"\u23f0 *Renewal Reminder \u2014 SubTrack*\n\n"
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


# ── Reminder-only job (no Gmail scan) ─────────────────────────────────────────
def run_reminders_only():
    """Load the cached report and fire any due reminders — no Gmail login needed."""
    cfg        = load_config()
    tg_token   = cfg.get("telegram_token", "").strip()
    tg_chat_id = cfg.get("telegram_chat_id", "").strip()
    if not tg_token or not tg_chat_id:
        log.warning("No Telegram credentials configured — skipping reminders.")
        return

    from analyzer import run_analysis
    report  = run_analysis()
    reminded = fire_renewal_reminders(report, tg_token, tg_chat_id)
    log.info(f"Reminder check done — {reminded} reminder(s) sent.")


# ── Full weekly scan job ───────────────────────────────────────────────────────
def run_full_scan():
    cfg          = load_config()
    email_addr   = cfg.get("email_addr", "").strip()
    app_password = cfg.get("app_password", "").strip()
    tg_token     = cfg.get("telegram_token", "").strip()
    tg_chat_id   = cfg.get("telegram_chat_id", "").strip()
    budget_usd   = cfg.get("budget_usd", 0)

    if not email_addr or not app_password:
        log.error("No Gmail credentials in alerts_config.json. Open the app and connect first.")
        return

    log.info("Starting weekly scan…")
    try:
        from parser import run_parser
        new_records = run_parser(email_addr, app_password)

        from analyzer import run_analysis
        report = run_analysis()

        cfg["last_scan"] = datetime.now(timezone.utc).isoformat()
        save_config(cfg)

        count   = report.get("merchant_count", 0)
        spend   = report.get("spend_by_currency", {})
        savings = report.get("potential_monthly_savings", 0)

        if tg_token and tg_chat_id:
            lines = ["*SubTrack \u2014 Weekly Digest* \ud83d\udcca\n"]
            lines.append(f"\ud83d\udc40 *{count}* active subscription{'s' if count != 1 else ''}")
            if spend:
                lines.append(
                    "\ud83d\udcb3 Monthly: *"
                    + " \u00b7 ".join(f"{CURRENCY_SYMBOLS.get(c,c)}{a:,.2f}" for c, a in spend.items())
                    + "*"
                )
            if savings > 0:
                lines.append(f"\u2728 Potential savings: *${savings:,.2f}/mo* (duplicate services)")

            usd_spend = spend.get("USD", 0)
            if budget_usd and usd_spend > budget_usd:
                over = usd_spend - budget_usd
                lines.append(f"\n\u26a0\ufe0f *Over budget!* ${usd_spend:,.2f}/mo vs ${budget_usd:,.2f} limit (${over:,.2f} over)")

            if new_records:
                lines.append(f"\n\ud83c\udd95 *{len(new_records)} new* email{'s' if len(new_records) != 1 else ''} detected")

            send_telegram(tg_token, tg_chat_id, "\n".join(lines))

            # Also fire any due reminders as part of weekly scan
            reminded = fire_renewal_reminders(report, tg_token, tg_chat_id)
            if reminded:
                log.info(f"Sent {reminded} renewal reminder(s).")

        log.info(
            f"Weekly scan complete — {len(new_records)} new records, "
            f"{count} merchants, {len(report.get('upcoming_renewals_30d', []))} upcoming renewals."
        )

    except Exception as exc:
        log.error(f"Scan failed: {exc}")
        if tg_token and tg_chat_id:
            try:
                send_telegram(tg_token, tg_chat_id, f"\u26a0\ufe0f *SubTrack scan failed*\n`{exc}`")
            except Exception:
                pass


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--once" in args:
        # Single full scan, then exit
        run_full_scan()

    elif "--remind" in args:
        # Daily reminder-only loop (no Gmail scan)
        log.info("Scheduling daily reminder check at 09:00…")
        schedule.every().day.at("09:00").do(run_reminders_only)
        run_reminders_only()       # run immediately on first start
        while True:
            schedule.run_pending()
            time.sleep(30)

    else:
        # Weekly full scan (Mondays 08:00) + run immediately
        log.info("Scheduling weekly scan (Mondays at 08:00)…")
        schedule.every().monday.at("08:00").do(run_full_scan)
        run_full_scan()            # run immediately on first start
        while True:
            schedule.run_pending()
            time.sleep(30)
