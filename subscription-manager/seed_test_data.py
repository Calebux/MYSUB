"""
seed_test_data.py — writes realistic mock subscription data for testing.
Run this to try the analyzer and dashboard without a Gmail connection.
"""
import json
from pathlib import Path
from datetime import date, timedelta
import hashlib, random

OUTPUT = Path("subscriptions.jsonl")

def make_records():
    today = date.today()

    subs = [
        # (merchant, from_email, amount, currency, freq_days, keyword, months_back)
        ("Netflix",     "info@mailer.netflix.com",     15.49, "USD", 30,  "subscription", 11),
        ("Netflix",     "info@mailer.netflix.com",     15.49, "USD", 30,  "subscription",  8),
        ("Netflix",     "info@mailer.netflix.com",     15.49, "USD", 30,  "subscription",  5),
        ("Netflix",     "info@mailer.netflix.com",     15.49, "USD", 30,  "subscription",  2),
        ("Spotify",     "no-reply@spotify.com",         9.99, "USD", 30,  "receipt",       10),
        ("Spotify",     "no-reply@spotify.com",         9.99, "USD", 30,  "receipt",        7),
        ("Spotify",     "no-reply@spotify.com",         9.99, "USD", 30,  "receipt",        4),
        ("Spotify",     "no-reply@spotify.com",         9.99, "USD", 30,  "receipt",        1),
        ("Apple Music", "no_reply@email.apple.com",    10.99, "USD", 30,  "billing",        9),  # overlap with Spotify
        ("Apple Music", "no_reply@email.apple.com",    10.99, "USD", 30,  "billing",        6),
        ("Apple Music", "no_reply@email.apple.com",    10.99, "USD", 30,  "billing",        3),
        ("OpenAI",      "billing@openai.com",          20.00, "USD", 30,  "invoice",       11),
        ("OpenAI",      "billing@openai.com",          20.00, "USD", 30,  "invoice",        8),
        ("OpenAI",      "billing@openai.com",          20.00, "USD", 30,  "invoice",        5),
        ("OpenAI",      "billing@openai.com",          20.00, "USD", 30,  "invoice",        2),
        ("Anthropic",   "billing@anthropic.com",       18.00, "USD", 30,  "invoice",        7),  # overlap with OpenAI
        ("Anthropic",   "billing@anthropic.com",       18.00, "USD", 30,  "invoice",        4),
        ("Anthropic",   "billing@anthropic.com",       18.00, "USD", 30,  "invoice",        1),
        ("GitHub",      "noreply@github.com",           4.00, "USD", 30,  "renewal",       11),
        ("GitHub",      "noreply@github.com",           4.00, "USD", 30,  "renewal",        8),
        ("GitHub",      "noreply@github.com",           4.00, "USD", 30,  "renewal",        5),
        ("GitHub",      "noreply@github.com",           4.00, "USD", 30,  "renewal",        2),
        ("Dropbox",     "no-reply@dropbox.com",        11.99, "USD", 365, "charged",       10),  # yearly → forgotten
        ("Adobe",       "mail@adobe.com",              54.99, "USD", 30,  "receipt",       11),
        ("Adobe",       "mail@adobe.com",              54.99, "USD", 30,  "receipt",        8),
        ("Adobe",       "mail@adobe.com",              54.99, "USD", 30,  "receipt",        5),
        ("Adobe",       "mail@adobe.com",              54.99, "USD", 30,  "receipt",        2),
        ("Notion",      "team@mail.notion.so",         16.00, "USD", 30,  "invoice",       10),
        ("Notion",      "team@mail.notion.so",         16.00, "USD", 30,  "invoice",        7),
        ("Notion",      "team@mail.notion.so",         16.00, "USD", 30,  "invoice",        4),
        ("NordVPN",     "no-reply@nordvpn.com",        11.99, "USD", 365, "renewal",        9),  # yearly → forgotten
        ("Duolingo",    "hello@duolingo.com",           6.99, "USD", 30,  "subscription",  11),
        ("Duolingo",    "hello@duolingo.com",           6.99, "USD", 30,  "subscription",   8),
        ("Duolingo",    "hello@duolingo.com",           6.99, "USD", 30,  "subscription",   5),
    ]

    records = []
    for merchant, from_email, amount, currency, freq_days, keyword, months_back in subs:
        charge_date = today - timedelta(days=months_back * 30)
        uid = f"{merchant}-{charge_date.isoformat()}"
        record_id = hashlib.sha256(uid.encode()).hexdigest()[:16]
        records.append({
            "id": record_id,
            "merchant": merchant,
            "amount": amount,
            "currency": currency,
            "date": charge_date.isoformat(),
            "subject": f"Your {merchant} {keyword} for {charge_date.strftime('%B %Y')}",
            "source_email": f"Test User <{from_email}>",
            "detected_keywords": [keyword, "payment"],
            "parsed_at": f"{charge_date.isoformat()}T12:00:00+00:00",
        })
    return records

if __name__ == "__main__":
    records = make_records()
    OUTPUT.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    print(f"Wrote {len(records)} mock records to {OUTPUT}")
