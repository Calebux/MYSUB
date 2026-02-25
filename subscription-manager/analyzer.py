"""
analyzer.py — Subscription Data Analyzer

Reads subscriptions.jsonl, groups by merchant, detects overlaps,
identifies forgotten subscriptions, predicts renewal dates, and
produces a structured JSON report.
"""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path
from statistics import median, stdev
from typing import Optional

log = logging.getLogger(__name__)

DATA_FILE = Path("subscriptions.jsonl")

# ── Category mapping ──────────────────────────────────────────────────────────
# Maps lowercase keywords in merchant names to a normalized category.
CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["openai", "anthropic", "claude", "gemini", "copilot", "midjourney", "jasper", "writesonic", "perplexity"], "AI Tools"),
    (["netflix", "hulu", "disney", "hbo", "max", "peacock", "paramount", "apple tv", "prime video", "crunchyroll"], "Streaming Video"),
    (["spotify", "apple music", "tidal", "deezer", "pandora", "youtube music", "soundcloud"], "Music Streaming"),
    (["github", "gitlab", "jira", "confluence", "notion", "linear", "asana", "trello", "basecamp", "monday"], "Dev / Project Mgmt"),
    (["dropbox", "google one", "icloud", "onedrive", "box", "backblaze", "carbonite"], "Cloud Storage"),
    (["adobe", "figma", "canva", "sketch", "invision", "procreate"], "Design Tools"),
    (["aws", "gcp", "azure", "digitalocean", "vercel", "netlify", "heroku", "render", "railway"], "Cloud Hosting"),
    (["zoom", "slack", "teams", "webex", "meet", "loom"], "Communication"),
    (["nytimes", "washington post", "wsj", "medium", "substack", "economist", "bloomberg"], "News / Media"),
    (["shopify", "squarespace", "wix", "wordpress", "webflow"], "Website Builders"),
    (["duolingo", "masterclass", "coursera", "udemy", "pluralsight", "linkedin learning"], "Education"),
    (["grammarly", "hemingway", "prowritingaid"], "Writing Tools"),
    (["1password", "lastpass", "dashlane", "bitwarden", "nordpass"], "Password Managers"),
    (["nordvpn", "expressvpn", "surfshark", "mullvad", "protonvpn"], "VPN"),
    (["xero", "quickbooks", "freshbooks", "wave", "bench"], "Accounting"),
]

def categorize(merchant: str) -> str:
    """Assign a category to a merchant name."""
    lower = merchant.lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in lower for kw in keywords):
            return category
    return "Other"


# ── Data loading ──────────────────────────────────────────────────────────────
def load_subscriptions(filepath: Path = DATA_FILE) -> list[dict]:
    """Load all records from the JSONL file."""
    records = []
    if not filepath.exists():
        return records
    with filepath.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


# ── Frequency detection ───────────────────────────────────────────────────────
def detect_frequency(dates: list[date]) -> Optional[str]:
    """
    Given a sorted list of charge dates, detect billing frequency.
    Returns 'monthly', 'yearly', 'quarterly', or None.
    """
    if len(dates) < 2:
        return None

    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    avg_gap = sum(gaps) / len(gaps)

    if 25 <= avg_gap <= 35:
        return "monthly"
    if 80 <= avg_gap <= 100:
        return "quarterly"
    if 340 <= avg_gap <= 390:
        return "yearly"
    return None


def predict_next_renewal(dates: list[date], frequency: Optional[str]) -> Optional[str]:
    """Predict the next renewal date based on frequency and last charge date."""
    if not dates or not frequency:
        return None
    last = max(dates)
    if frequency == "monthly":
        # Add ~30 days
        next_d = last + timedelta(days=30)
    elif frequency == "quarterly":
        next_d = last + timedelta(days=91)
    elif frequency == "yearly":
        next_d = last + timedelta(days=365)
    else:
        return None
    return next_d.isoformat()


# ── Per-merchant analysis ─────────────────────────────────────────────────────
def analyze_merchant(merchant: str, records: list[dict]) -> dict:
    """Produce a summary dict for a single merchant."""
    amounts = [r["amount"] for r in records if r.get("amount") is not None]
    dates_raw = []
    for r in records:
        try:
            dates_raw.append(date.fromisoformat(r["date"]))
        except (ValueError, KeyError):
            pass
    dates_raw.sort()

    frequency = detect_frequency(dates_raw)
    last_charge = max(dates_raw).isoformat() if dates_raw else None
    days_since_last = (date.today() - max(dates_raw)).days if dates_raw else None
    next_renewal = predict_next_renewal(dates_raw, frequency)

    # Best-guess monthly cost
    avg_amount = round(sum(amounts) / len(amounts), 2) if amounts else 0.0
    if frequency == "yearly":
        monthly_cost = round(avg_amount / 12, 2)
    elif frequency == "quarterly":
        monthly_cost = round(avg_amount / 3, 2)
    else:
        monthly_cost = avg_amount  # monthly or unknown → treat as monthly

    yearly_cost = round(monthly_cost * 12, 2)

    category = categorize(merchant)

    return {
        "merchant": merchant,
        "category": category,
        "charge_count": len(records),
        "avg_amount": avg_amount,
        "currency": records[0].get("currency", "USD") if records else "USD",
        "frequency": frequency,
        "monthly_cost": monthly_cost,
        "yearly_cost": yearly_cost,
        "last_charge": last_charge,
        "days_since_last": days_since_last,
        "next_renewal": next_renewal,
        "dates": [d.isoformat() for d in dates_raw],
        "is_forgotten": (days_since_last is not None and days_since_last > 90 and frequency is not None),
    }


# ── Overlap detection ─────────────────────────────────────────────────────────
OVERLAP_TOLERANCE = 0.30  # 30% price similarity threshold

def detect_overlaps(merchant_summaries: list[dict]) -> list[dict]:
    """
    Flag merchants in the same category with similar prices as potential duplicates.
    Returns a list of overlap warning dicts.
    """
    overlaps = []
    by_category: dict[str, list[dict]] = defaultdict(list)
    for m in merchant_summaries:
        if m["category"] != "Other":
            by_category[m["category"]].append(m)

    for category, group in by_category.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a["monthly_cost"] == 0 or b["monthly_cost"] == 0:
                    continue
                ratio = abs(a["monthly_cost"] - b["monthly_cost"]) / max(a["monthly_cost"], b["monthly_cost"])
                if ratio <= OVERLAP_TOLERANCE:
                    overlaps.append({
                        "category": category,
                        "merchant_a": a["merchant"],
                        "merchant_b": b["merchant"],
                        "monthly_cost_a": a["monthly_cost"],
                        "monthly_cost_b": b["monthly_cost"],
                        "potential_savings": min(a["monthly_cost"], b["monthly_cost"]),
                        "reason": f"Both are {category} tools with similar pricing (${a['monthly_cost']}/mo vs ${b['monthly_cost']}/mo).",
                    })
    return overlaps


# ── Upcoming renewals ─────────────────────────────────────────────────────────
def upcoming_renewals(merchant_summaries: list[dict], days: int = 30) -> list[dict]:
    """Return merchants whose predicted next renewal falls within `days` days."""
    today = date.today()
    horizon = today + timedelta(days=days)
    upcoming = []
    for m in merchant_summaries:
        if not m.get("next_renewal"):
            continue
        try:
            renewal_date = date.fromisoformat(m["next_renewal"])
        except ValueError:
            continue
        if today <= renewal_date <= horizon:
            days_until = (renewal_date - today).days
            upcoming.append({
                "merchant": m["merchant"],
                "amount": m["avg_amount"],
                "currency": m["currency"],
                "renewal_date": m["next_renewal"],
                "days_until": days_until,
            })
    upcoming.sort(key=lambda x: x["days_until"])
    return upcoming


# ── Main analysis entry point ─────────────────────────────────────────────────
def run_analysis(filepath: Path = DATA_FILE) -> dict:
    """
    Run the full analysis pipeline and return a structured report dict.

    Report structure:
    {
        "generated_at": "...",
        "total_records": N,
        "merchant_count": N,
        "total_monthly_spend": X.XX,
        "total_yearly_spend": X.XX,
        "potential_monthly_savings": X.XX,   # sum of savings from overlaps
        "merchants": [...],
        "overlaps": [...],
        "forgotten_subscriptions": [...],
        "upcoming_renewals_30d": [...],
    }
    """
    records = load_subscriptions(filepath)
    if not records:
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "total_records": 0,
            "merchant_count": 0,
            "total_monthly_spend": 0.0,
            "total_yearly_spend": 0.0,
            "potential_monthly_savings": 0.0,
            "merchants": [],
            "overlaps": [],
            "forgotten_subscriptions": [],
            "upcoming_renewals_30d": [],
        }

    # Split active vs cancelled records
    by_merchant: dict[str, list[dict]] = defaultdict(list)
    cancelled_by_merchant: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("status") == "cancelled":
            cancelled_by_merchant[r["merchant"]].append(r)
        else:
            by_merchant[r["merchant"]].append(r)

    # Analyze each merchant
    merchant_summaries = [
        analyze_merchant(merchant, recs)
        for merchant, recs in by_merchant.items()
    ]
    merchant_summaries.sort(key=lambda m: m["monthly_cost"], reverse=True)

    # Aggregate totals — grouped by currency so NGN and USD aren't mixed
    spend_by_currency: dict[str, float] = defaultdict(float)
    for m in merchant_summaries:
        spend_by_currency[m["currency"]] = round(
            spend_by_currency[m["currency"]] + m["monthly_cost"], 2
        )
    # Keep a USD-only total for backwards compat; full breakdown in spend_by_currency
    total_monthly = spend_by_currency.get("USD", 0.0)
    total_yearly  = round(total_monthly * 12, 2)

    # Overlaps
    overlaps = detect_overlaps(merchant_summaries)
    potential_savings = round(sum(o["potential_savings"] for o in overlaps), 2)

    # Forgotten subscriptions
    forgotten = [m for m in merchant_summaries if m["is_forgotten"]]

    # Upcoming renewals
    renewals = upcoming_renewals(merchant_summaries, days=30)

    # Recently cancelled subscriptions
    recently_cancelled = []
    for merchant, recs in cancelled_by_merchant.items():
        # Skip if they still have active charges from same merchant
        if merchant in by_merchant:
            continue
        dates_raw = []
        for r in recs:
            try:
                dates_raw.append(date.fromisoformat(r["date"]))
            except (ValueError, KeyError):
                pass
        last_seen = max(dates_raw).isoformat() if dates_raw else None
        # Find last known amount from active history or cancellation email
        amounts = [r["amount"] for r in recs if r.get("amount")]
        recently_cancelled.append({
            "merchant": merchant,
            "category": categorize(merchant),
            "cancelled_date": last_seen,
            "last_amount": amounts[0] if amounts else None,
            "currency": recs[0].get("currency", "USD"),
        })
    recently_cancelled.sort(key=lambda x: x["cancelled_date"] or "", reverse=True)

    # Monthly spend trend (per currency, active subs only)
    monthly_by_currency: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in records:
        if r.get("status") == "cancelled":
            continue
        try:
            month = r["date"][:7]  # YYYY-MM
            currency = r.get("currency", "USD")
            amount = r.get("amount") or 0
            monthly_by_currency[currency][month] = round(
                monthly_by_currency[currency].get(month, 0) + amount, 2
            )
        except (KeyError, TypeError):
            pass
    monthly_trend = {
        currency: [{"month": m, "amount": a} for m, a in sorted(months.items())]
        for currency, months in monthly_by_currency.items()
    }

    # Category spend breakdown (active subs, monthly cost)
    cat_spend: dict[str, float] = defaultdict(float)
    for m in merchant_summaries:
        cat_spend[m["category"]] = round(cat_spend[m["category"]] + m["monthly_cost"], 2)
    category_breakdown = sorted(
        [{"category": cat, "monthly_cost": amt} for cat, amt in cat_spend.items()],
        key=lambda x: -x["monthly_cost"],
    )

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_records": len(records),
        "merchant_count": len(merchant_summaries),
        "total_monthly_spend": total_monthly,
        "total_yearly_spend": total_yearly,
        "spend_by_currency": dict(spend_by_currency),
        "potential_monthly_savings": potential_savings,
        "merchants": merchant_summaries,
        "overlaps": overlaps,
        "forgotten_subscriptions": forgotten,
        "upcoming_renewals_30d": renewals,
        "recently_cancelled": recently_cancelled,
        "monthly_trend": monthly_trend,
        "category_breakdown": category_breakdown,
    }

    log.info(
        f"Analysis complete: {len(merchant_summaries)} merchants | "
        f"${total_monthly}/mo | {len(overlaps)} overlaps | "
        f"{len(forgotten)} forgotten | {len(renewals)} renewals in 30d"
    )
    return report


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    report = run_analysis()
    output_path = Path("report.json")
    output_path.write_text(json.dumps(report, indent=2))
    print(f"Report saved to {output_path}")
    print(f"  Total monthly spend : ${report['total_monthly_spend']}")
    print(f"  Potential savings   : ${report['potential_monthly_savings']}/mo")
    print(f"  Renewals in 30 days : {len(report['upcoming_renewals_30d'])}")
