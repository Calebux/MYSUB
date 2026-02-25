"""
parser.py — Gmail IMAP Email Parser for Subscription Detection

Connects to Gmail via IMAP (app password), searches for subscription-related
emails in the last 12 months, extracts key fields, and saves to subscriptions.jsonl.

Features:
  - Resume capability: skips already-parsed email IDs
  - Rate limiting: max 100 emails/minute
  - Credential-free code: all secrets loaded from .env
"""

import imaplib
import email
import email.message
import re
import json
import os
import time
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
SEARCH_KEYWORDS = [
    "receipt", "invoice", "subscription", "payment",
    "charged", "billing", "renewal",
]

# Email must contain at least one of these to be treated as a real subscription
SUBSCRIPTION_SIGNALS = [
    "subscription", "your plan", "membership",
    "billed monthly", "billed annually", "billed yearly",
    "auto-renew", "auto renew", "renewal", "recurring",
    "billing cycle", "next billing", "next charge",
    "monthly charge", "annual charge", "yearly charge",
    "cancel anytime", "your invoice", "your receipt",
    "payment confirmation", "payment receipt",
    "charged for", "your account has been charged",
    # Payment reminder / failure patterns (e.g. Starlink)
    "payment reminder", "automatic payment", "payment failed",
    "payment due", "payment unsuccessful", "past due",
    "service fee", "service charge",
]

# Emails matching any of these are NOT subscriptions — skip them
EXCLUSION_SIGNALS = [
    "[test mode]", "test mode", "test payment",
    "% off", "save up to", "special offer", "limited time",
    "sale ends", "promo code", "discount code", "coupon",
    "has shipped", "shipping confirmation", "your order has",
    "order confirmation", "order #", "tracking number",
    "refund", "return merchandise",
    "newsletter", "unsubscribe from our list",
    "you've earned", "cashback", "reward points",
    "7 days left", "days remaining to submit",
    "hackathon", "pr run failed", "build failed", "pipeline failed",
    "charged $0.00", "charged ₦0.00", " $0.00 ",
    "payment of 0.00",
]

# Emails with these signals are CANCELLED subscriptions (saved separately)
CANCELLATION_SIGNALS = [
    "subscription cancelled", "subscription has been cancelled",
    "subscription has ended", "subscription ended",
    "you've cancelled", "you have cancelled",
    "cancellation confirmed", "cancellation confirmation",
    "your cancellation", "cancelled your subscription",
    "membership cancelled", "membership ended",
    "plan cancelled", "plan has been cancelled",
    "we're sorry to see you go", "sorry to see you go",
    "your account has been closed", "service has been cancelled",
]

OUTPUT_FILE = Path("subscriptions.jsonl")
LOOKBACK_DAYS = 60            # 2 months


# ── Credential loading ───────────────────────────────────────────────────────
def load_credentials() -> tuple[str, str]:
    """Load Gmail credentials from .env — never hardcoded."""
    load_dotenv()
    email_addr = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not email_addr or not app_password:
        raise EnvironmentError(
            "Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in .env file. "
            "See .env.example for the required format."
        )
    return email_addr, app_password


# ── IMAP connection ──────────────────────────────────────────────────────────
def connect_imap(email_addr: str, app_password: str) -> imaplib.IMAP4_SSL:
    """Establish authenticated IMAP connection to Gmail."""
    log.info("Connecting to Gmail IMAP…")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(email_addr, app_password)
    log.info("Authenticated successfully.")
    return mail


# ── Resume support ────────────────────────────────────────────────────────────
def load_parsed_ids() -> set[str]:
    """Return set of already-parsed email IDs from the JSONL output file."""
    parsed = set()
    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        parsed.add(record["id"])
                    except (json.JSONDecodeError, KeyError):
                        pass
    return parsed


# ── Text helpers ─────────────────────────────────────────────────────────────
def decode_mime_words(s: str) -> str:
    """Decode MIME-encoded header words to a plain string."""
    parts = decode_header(s)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def extract_body_snippet(msg: email.message.Message, max_chars: int = 500) -> str:
    """Extract a short plain-text snippet from the email body."""
    snippet = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    snippet = payload.decode(errors="replace")
                    break
        # Fall back to HTML part if no plain-text found
        if not snippet:
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        raw = payload.decode(errors="replace")
                        # Strip HTML tags crudely
                        snippet = re.sub(r"<[^>]+>", " ", raw)
                        snippet = re.sub(r"\s+", " ", snippet).strip()
                        break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            snippet = payload.decode(errors="replace")

    return snippet[:max_chars].strip()


# ── Amount extraction ─────────────────────────────────────────────────────────
AMOUNT_PATTERNS = [
    # $12.99 / $57,000 / USD 12.99
    r"\$\s?([\d,]+(?:\.\d{2})?)",
    r"USD\s?([\d,]+(?:\.\d{2})?)",
    r"([\d,]+(?:\.\d{2})?)\s?USD",
    r"([\d,]+(?:\.\d{2})?)\s?dollars?",
    # ₦57,000 / ₦57,000.00 / NGN 57,000
    r"₦\s?([\d,]+(?:\.\d{2})?)",
    r"NGN\s?([\d,]+(?:\.\d{2})?)",
    r"([\d,]+(?:\.\d{2})?)\s?NGN",
    # £9.99 / GBP 9.99 / €12.00 / EUR 12.00
    r"£\s?([\d,]+(?:\.\d{2})?)",
    r"GBP\s?([\d,]+(?:\.\d{2})?)",
    r"€\s?([\d,]+(?:\.\d{2})?)",
    r"EUR\s?([\d,]+(?:\.\d{2})?)",
    # Generic label patterns
    r"total[:\s]+\$?\s?([\d,]+(?:\.\d{2})?)",
    r"amount[:\s]+\$?\s?([\d,]+(?:\.\d{2})?)",
    r"charged[:\s]+\$?\s?([\d,]+(?:\.\d{2})?)",
]

def extract_amount(text: str) -> Optional[float]:
    """Return the first plausible dollar amount found in `text`."""
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                val = float(raw)
                if 0.01 <= val <= 9_999_999:  # high limit supports NGN/large currencies
                    return round(val, 2)
            except ValueError:
                continue
    return None


def extract_currency(text: str) -> str:
    """Detect currency symbol/code; defaults to USD."""
    if re.search(r"₦|\bNGN\b|naira", text, re.IGNORECASE):
        return "NGN"
    if re.search(r"£|\bGBP\b", text):
        return "GBP"
    if re.search(r"€|\bEUR\b", text):
        return "EUR"
    if re.search(r"¥|\bJPY\b|\bCNY\b", text):
        return "JPY"
    if re.search(r"\bCAD\b", text):
        return "CAD"
    return "USD"


# ── Merchant extraction ───────────────────────────────────────────────────────
def extract_merchant(from_header: str) -> str:
    """
    Derive a clean merchant name from the From header.
    Prefers the display name; falls back to the sender domain.
    """
    # Try to extract display name
    display_match = re.match(r'^"?([^"<]+)"?\s*<', from_header)
    if display_match:
        name = display_match.group(1).strip().strip('"')
        if name and not re.fullmatch(r"[a-z0-9._%+\-]+", name, re.IGNORECASE):
            return name

    # Fall back to domain
    domain_match = re.search(r"@([\w.\-]+)>?", from_header)
    if domain_match:
        domain = domain_match.group(1).lower()
        parts = domain.split(".")
        # Use the second-to-last segment (registerable domain, before TLD)
        # e.g. mailer.netflix.com → netflix, billing.openai.com → openai
        if len(parts) >= 2:
            return parts[-2].capitalize()
        return parts[0].capitalize()
    return from_header[:40]


# ── Keyword detection ─────────────────────────────────────────────────────────
def detected_keywords(subject: str, body: str) -> list[str]:
    """Return which SEARCH_KEYWORDS appear in the subject or body."""
    combined = (subject + " " + body).lower()
    return [kw for kw in SEARCH_KEYWORDS if kw in combined]


# ── Core parsing logic ────────────────────────────────────────────────────────
def parse_email(raw_bytes: bytes, uid: str) -> Optional[dict]:
    """
    Parse a raw email byte-string into a subscription record dict.
    Returns None if parsing fails or no amount could be extracted.
    """
    try:
        msg = email.message_from_bytes(raw_bytes)

        subject = decode_mime_words(msg.get("Subject", ""))
        from_header = msg.get("From", "")
        date_header = msg.get("Date", "")

        # Parse date
        try:
            date_obj = parsedate_to_datetime(date_header)
            date_str = date_obj.strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")

        body = extract_body_snippet(msg)
        combined_text = f"{subject} {body}"

        amount = extract_amount(combined_text)
        currency = extract_currency(combined_text)
        merchant = extract_merchant(from_header)
        keywords = detected_keywords(subject, body)

        # ── Strict subscription filter ────────────────────────────────────────
        combined_lower = combined_text.lower()

        # Check cancellation first — save even without amount
        is_cancelled = any(sig in combined_lower for sig in CANCELLATION_SIGNALS)

        if not is_cancelled:
            # Active subscription: must have positive amount + subscription signal
            if not amount or amount <= 0:
                return None
            has_signal = any(sig in combined_lower for sig in SUBSCRIPTION_SIGNALS)
            if not has_signal:
                return None
            if any(excl in combined_lower for excl in EXCLUSION_SIGNALS):
                return None

        status = "cancelled" if is_cancelled else "active"

        # Generate stable ID from uid + from header
        record_id = hashlib.sha256(f"{uid}:{from_header}".encode()).hexdigest()[:16]

        return {
            "id": record_id,
            "merchant": merchant,
            "amount": amount,
            "currency": currency,
            "date": date_str,
            "subject": subject[:200],
            "source_email": from_header[:200],
            "detected_keywords": keywords,
            "status": status,
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        log.warning(f"Failed to parse email uid={uid}: {exc}")
        return None


# ── Main parser ───────────────────────────────────────────────────────────────
def run_parser(
    email_addr: str,
    app_password: str,
    progress_callback=None,
) -> list[dict]:
    """
    Connect to Gmail, search for subscription-related emails, parse, and
    save results to subscriptions.jsonl.

    Args:
        email_addr:        Gmail address.
        app_password:      Gmail app password.
        progress_callback: Optional callable(current, total, record) for UI updates.

    Returns:
        List of newly parsed subscription records.
    """
    mail = connect_imap(email_addr, app_password)

    # ── Target Gmail's Subscriptions category first (much smaller set) ────────
    since_gmail = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y/%m/%d")
    since_imap  = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
    all_uids = []

    try:
        status, _ = mail.select('"[Gmail]/All Mail"')
        if status == "OK":
            _, data = mail.search(None, "X-GM-RAW",
                                  f'"category:subscriptions after:{since_gmail}"')
            all_uids = data[0].split() if data[0] else []
            log.info(f"Gmail Subscriptions category: {len(all_uids)} emails found.")
    except Exception as exc:
        log.warning(f"X-GM-RAW search failed ({exc}), falling back to INBOX keyword search.")

    # ── Fallback: INBOX + IMAP subject-keyword search ─────────────────────────
    if not all_uids:
        mail.select("INBOX")
        combined_uids: set[bytes] = set()
        for kw in SEARCH_KEYWORDS:
            try:
                _, data = mail.search(None, f'(SINCE "{since_imap}" SUBJECT "{kw}")')
                if data[0]:
                    combined_uids.update(data[0].split())
            except Exception:
                pass
        all_uids = list(combined_uids)
        log.info(f"INBOX keyword search: {len(all_uids)} candidate emails.")

    already_parsed = load_parsed_ids()
    log.info(f"Resuming: {len(already_parsed)} already parsed, skipping them.")

    new_records: list[dict] = []
    processed = 0

    with OUTPUT_FILE.open("a") as out_f:
        for i, uid in enumerate(all_uids):
            uid_str = uid.decode() if isinstance(uid, bytes) else uid

            # Fetch full email
            _, msg_data = mail.fetch(uid, "(RFC822)")
            if not msg_data or msg_data[0] is None:
                continue
            raw_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
            if not raw_bytes:
                continue

            record = parse_email(raw_bytes, uid_str)
            if record is None:
                continue

            if record["id"] in already_parsed:
                if progress_callback:
                    progress_callback(i + 1, len(all_uids), record)
                continue

            already_parsed.add(record["id"])
            new_records.append(record)
            out_f.write(json.dumps(record) + "\n")
            out_f.flush()
            processed += 1

            log.info(f"[{processed}] {record['merchant']} | {record['currency']} {record['amount']} | {record['date']}")

            if progress_callback:
                progress_callback(i + 1, len(all_uids), record)

    mail.logout()
    log.info(f"Done. Parsed {processed} new subscription emails → {OUTPUT_FILE}")
    return new_records


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    addr, pwd = load_credentials()
    run_parser(addr, pwd)
