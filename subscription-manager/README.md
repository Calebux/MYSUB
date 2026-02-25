# SubTrack — Subscription Management Tool

Automatically discovers and analyzes your subscription charges from Gmail, detects duplicates, finds forgotten services, and predicts upcoming renewals.

---

## Architecture

```
subscription-manager/
├── parser.py          # Gmail IMAP scraper → subscriptions.jsonl
├── analyzer.py        # Analysis engine → structured report
├── app.py             # Streamlit dashboard (calls parser + analyzer)
├── requirements.txt
├── .env.example       # Credential template
└── .gitignore
```

---

## Quick Start

### 1. Clone / copy the project

```bash
cd subscription-manager
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Gmail credentials

**a) Enable 2-Step Verification** on your Google account at
`https://myaccount.google.com/security`

**b) Generate an App Password** at
`https://myaccount.google.com/apppasswords`
→ Select app: *Mail* → Select device: *Other (custom)* → Copy the 16-character code.

**c) Create your `.env` file:**

```bash
cp .env.example .env
```

Edit `.env`:

```env
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

> Your `.env` is listed in `.gitignore` and will never be committed.

---

## Running the Dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The four-step wizard guides you through:

1. **Connect** — enter your Gmail address and App Password
2. **Scanning** — live progress as emails are parsed (resumes if interrupted)
3. **Results** — summary cards, duplicate warnings, upcoming renewals, full subscription list
4. **Actions** — export JSON audit, download cancellation script, download renewal checklist

---

## Running Components Standalone

### Parser only

```bash
python parser.py
```

Writes results to `subscriptions.jsonl`.
Subsequent runs skip already-parsed emails (resume capability).

### Analyzer only

```bash
python analyzer.py
```

Reads `subscriptions.jsonl` and writes `report.json`.

---

## Output Files

| File | Description |
|------|-------------|
| `subscriptions.jsonl` | One JSON record per subscription email found |
| `report.json` | Full analysis report (merchants, overlaps, renewals, etc.) |

### subscriptions.jsonl record format

```json
{
  "id":                "3a7f…",
  "merchant":          "Netflix",
  "amount":            15.49,
  "currency":          "USD",
  "date":              "2024-11-01",
  "subject":           "Your Netflix receipt",
  "source_email":      "info@mailer.netflix.com",
  "detected_keywords": ["receipt", "subscription"],
  "parsed_at":         "2025-01-15T10:23:45+00:00"
}
```

---

## Configuration

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | `parser.py` | `100` | Max emails processed per minute |
| `LOOKBACK_DAYS` | `parser.py` | `365` | How far back to search (days) |
| `OVERLAP_TOLERANCE` | `analyzer.py` | `0.30` | Price similarity threshold for duplicate detection (30%) |
| Output file | `parser.py` | `subscriptions.jsonl` | Path for parsed data |

---

## Security Notes

- Credentials are loaded exclusively from the `.env` file via `python-dotenv`.
- IMAP access is **read-only** — the tool never sends, deletes, or modifies emails.
- All data stays on your local machine.
- The `.env` file is in `.gitignore` to prevent accidental commits.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `IMAP authentication failed` | Verify App Password is correct; ensure 2FA is enabled |
| `Missing GMAIL_ADDRESS…` | Check that `.env` exists and has both variables set |
| `No records found` | Try expanding `LOOKBACK_DAYS`; ensure IMAP is enabled in Gmail settings |
| Dashboard shows no data | Run the parser first (Step 2) or place an existing `subscriptions.jsonl` in the same directory |

To enable IMAP in Gmail:
`Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP`
