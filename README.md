# MYSUB
# SubTrack — Subscription Management Tool
# SubTrack — Subscription Intelligence Dashboard

Automatically discovers and analyzes your subscription charges from Gmail, detects duplicates, finds forgotten services, and predicts upcoming renewals.
SubTrack scans your Gmail inbox for subscription receipts and billing emails, then gives you a clean dashboard showing exactly what you pay, what's renewing soon, what you've forgotten about, and what overlaps with something else you already pay for. It runs as a local web app and can be shared with friends over ngrok or self-hosted.

---

## Architecture
## What it does

- **Inbox scanning** — connects to Gmail via IMAP (read-only), searches the last 4 months of emails for receipts, invoices, billing confirmations, and renewal notices
- **Smart analysis** — groups charges by merchant, detects billing frequency (monthly / quarterly / yearly), calculates your true monthly cost, and predicts the next renewal date
- **Overlap detection** — finds subscriptions in the same category (e.g. two streaming video services, two VPNs) that you might be doubling up on
- **Forgotten subscription flagging** — surfaces services that haven't charged you in 90+ days but were recurring
- **Health scores** — each subscription gets a score (0–100) based on charge frequency, recency, cost, and overlap. Low-scoring ones are flagged for review
- **Upcoming renewals** — shows everything billing within the next 30 days with amounts and dates
- **Telegram alerts** — optional bot integration sends you a renewal reminder 3, 2, and 1 day before any subscription charges
- **Manual entries** — add subscriptions that don't send email receipts (e.g. cash payments, Apple In-App)
- **Cancellation shortcuts** — one-click links to the cancellation page for 60+ major services (Netflix, Spotify, Adobe, GitHub, etc.)
- **Audit export** — download the full parsed data as a JSON file

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend API | Python, FastAPI, Uvicorn |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Email scanning | Gmail IMAP (App Password) |
| Notifications | Telegram Bot API |
| Deployment | Any machine with Python 3.10+, exposed via ngrok or reverse proxy |

---

## Project Structure

```
subscription-manager/
├── parser.py          # Gmail IMAP scraper → subscriptions.jsonl
├── analyzer.py        # Analysis engine → structured report
├── app.py             # Streamlit dashboard (calls parser + analyzer)
├── requirements.txt
├── .env.example       # Credential template
└── .gitignore
├── api.py               # FastAPI backend — auth, scan, report, alerts endpoints
├── parser.py            # Gmail IMAP scraper → subscriptions.jsonl
├── analyzer.py          # Analysis engine → structured JSON report
├── scheduler.py         # Background job runner (daily renewal reminders)
├── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main dashboard + step router
│   │   ├── api.ts                     # Authenticated fetch wrapper
│   │   └── components/
│   │       ├── ConnectStep.tsx        # Gmail credentials form
│   │       ├── ScanningStep.tsx       # Live scan progress UI
│   │       ├── ActionsStep.tsx        # Export + Telegram config
│   │       └── AddSubscriptionModal.tsx
│   └── dist/                          # Built frontend (served by FastAPI)
└── data/
    ├── tokens.json                    # Session tokens (auto-managed)
    └── {user_hash}/                   # Per-user isolated data directory
        ├── subscriptions.jsonl
        ├── report.json
        ├── alerts_config.json
        └── sent_alerts.json
```

---

## Quick Start
## Option A — Use the Hosted Version (ngrok)

If someone is running SubTrack on their machine and sharing it via ngrok, you just need a browser.

### 1. Clone / copy the project
1. Get the ngrok URL from whoever is hosting it (looks like `https://xyz.ngrok-free.app`)
2. Open the URL in your browser
3. Click **Connect your inbox**, enter your Gmail address and a Google App Password (see [How to get a Google App Password](#how-to-get-a-google-app-password) below)
4. SubTrack scans your inbox and shows your personal dashboard — your data is completely separate from any other user's

> Your credentials and subscription data are stored in an isolated directory on the host machine, keyed to a hash of your email address. No two users can see each other's data.

---

## Option B — Run it Yourself (Local Install)

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm

### 1. Clone the repository

```bash
cd subscription-manager
git clone https://github.com/Calebux/MYSUB.git
cd MYSUB
```

### 2. Create a virtual environment
### 2. Set up the Python backend

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Activate it
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Install dependencies
### 3. Build the frontend

```bash
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
```

### 4. Set up Gmail credentials
This produces a `frontend/dist/` folder that FastAPI serves automatically.

### 4. Start the server

```bash
.venv/bin/python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

**a) Enable 2-Step Verification** on your Google account at
`https://myaccount.google.com/security`
Open `http://localhost:8000` in your browser.

**b) Generate an App Password** at
`https://myaccount.google.com/apppasswords`
→ Select app: *Mail* → Select device: *Other (custom)* → Copy the 16-character code.
### 5. (Optional) Change the access password

**c) Create your `.env` file:**
By default the app uses `subtrack` as the internal access password. To change it, set the environment variable before starting:

```bash
cp .env.example .env
ACCESS_PASSWORD=mysecretpassword .venv/bin/python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

Edit `.env`:
Or create a `.env` file in the project root:

```env
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
ACCESS_PASSWORD=mysecretpassword
```

> Your `.env` is listed in `.gitignore` and will never be committed.

---

## Running the Dashboard
## Option C — Docker Container

### Build and run with Docker

```bash
streamlit run app.py
# Build the image
docker build -t subtrack .

# Run it
docker run -d \
  --name subtrack \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  subtrack
```

Open `http://localhost:8000`.

The `-v $(pwd)/data:/app/data` flag mounts a local `data/` folder into the container so your scan results, tokens, and alert configs persist across container restarts.

### Docker Compose (recommended for always-on setups)

Create a `docker-compose.yml` in the project root:

```yaml
version: "3.9"
services:
  subtrack:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - ACCESS_PASSWORD=yourpasswordhere
    restart: unless-stopped
```

Open `http://localhost:8501` in your browser. The four-step wizard guides you through:
Then start it with:

```bash
docker compose up -d
```

Stop it with:

```bash
docker compose down
```

### Dockerfile

Create a `Dockerfile` in the project root if it doesn't already exist:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY api.py parser.py analyzer.py scheduler.py ./

# Copy pre-built frontend (build it on your machine first with npm run build)
COPY frontend/dist ./frontend/dist

1. **Connect** — enter your Gmail address and App Password
2. **Scanning** — live progress as emails are parsed (resumes if interrupted)
3. **Results** — summary cards, duplicate warnings, upcoming renewals, full subscription list
4. **Actions** — export JSON audit, download cancellation script, download renewal checklist
# Data directory for persistent storage
RUN mkdir -p data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **Before building the Docker image**, build the frontend first on your machine:
> ```bash
> cd frontend && npm install && npm run build && cd ..
> ```
> The `frontend/dist/` folder is then copied into the image.

---

## Running Components Standalone
## Sharing Over the Internet with ngrok

If you want to let friends use your installation without buying a server, ngrok creates a secure tunnel to your local machine.

### Install ngrok

### Parser only
```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download
```

### Create a free ngrok account and get a static domain

1. Sign up at [ngrok.com](https://ngrok.com) (free)
2. Go to **Domains** in the dashboard and claim your free static domain (e.g. `your-name.ngrok-free.app`)
3. Copy your authtoken from the ngrok dashboard and run:

```bash
python parser.py
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

Writes results to `subscriptions.jsonl`.
Subsequent runs skip already-parsed emails (resume capability).
### Start the tunnel

### Analyzer only
In one terminal, start the server:

```bash
python analyzer.py
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Reads `subscriptions.jsonl` and writes `report.json`.
In a second terminal, start ngrok pointing at port 8000:

```bash
ngrok http --url=your-name.ngrok-free.app 8000
```

Share `https://your-name.ngrok-free.app` with your friends. As long as both processes are running, the link works.

> Both terminals must stay open. On Windows you can use two separate Command Prompt windows. On a server or always-on PC you can run them with `screen`, `tmux`, or as background services.

---

## Output Files
## How to Get a Google App Password

| File | Description |
|------|-------------|
| `subscriptions.jsonl` | One JSON record per subscription email found |
| `report.json` | Full analysis report (merchants, overlaps, renewals, etc.) |
SubTrack connects to Gmail using an **App Password** — a special 16-character code separate from your main Google password. It gives read-only IMAP access and can be revoked at any time.

### subscriptions.jsonl record format
1. Go to your Google account: [myaccount.google.com/security](https://myaccount.google.com/security)
2. Make sure **2-Step Verification** is turned on (required)
3. In the search bar at the top, search for **App Passwords**
4. Click **App Passwords**, then **Create**
5. Give it a name (e.g. "SubTrack") and click **Create**
6. Google shows you a 16-character code like `abcd efgh ijkl mnop` — copy it
7. Paste it into SubTrack's **Connect your inbox** form

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
> The App Password only works for IMAP access. SubTrack never sends, deletes, or modifies any of your emails.

To revoke access at any time, go back to App Passwords and delete the entry for SubTrack.

---

## Setting Up Telegram Alerts

SubTrack can send you a Telegram message 3, 2, and 1 day before any subscription renews.

### Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts (choose a name and username)
3. BotFather gives you a token like `7123456789:AABBccddEEff...` — copy it

### Step 2 — Get your Chat ID

1. Search for **@userinfobot** in Telegram
2. Send it any message
3. It replies with your Chat ID (a number like `123456789`)

### Step 3 — Configure in SubTrack

1. Go to step **4 · Actions** in the SubTrack dashboard
2. Paste your Bot Token and Chat ID into the Telegram Alerts card
3. Click **Save Telegram Config**
4. Click **Send Test Message** to confirm it works

After this, SubTrack will automatically send you a reminder message whenever a subscription is 3, 2, or 1 day away from renewing.

---

## Configuration
## Configuration Reference

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | `parser.py` | `100` | Max emails processed per minute |
| `LOOKBACK_DAYS` | `parser.py` | `365` | How far back to search (days) |
| `OVERLAP_TOLERANCE` | `analyzer.py` | `0.30` | Price similarity threshold for duplicate detection (30%) |
| Output file | `parser.py` | `subscriptions.jsonl` | Path for parsed data |
All configuration is done via environment variables (or a `.env` file in the project root).

| Variable | Default | Description |
|---|---|---|
| `ACCESS_PASSWORD` | `subtrack` | Password used to obtain a session token. Change this if sharing the app. |
| `GOOGLE_CLIENT_ID` | — | Optional. Only needed if you enable Google OAuth sign-in. |
| `GOOGLE_CLIENT_SECRET` | — | Optional. Only needed if you enable Google OAuth sign-in. |
| `BASE_URL` | `http://localhost:8000` | The public-facing URL of your deployment (used for OAuth redirect URI). |

---

## Security Notes
## API Endpoints

The FastAPI backend exposes the following endpoints (all `/api/*` routes require a Bearer token obtained from `/auth/login`):

- Credentials are loaded exclusively from the `.env` file via `python-dotenv`.
- IMAP access is **read-only** — the tool never sends, deletes, or modifies emails.
- All data stays on your local machine.
- The `.env` file is in `.gitignore` to prevent accidental commits.
| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/login` | Exchange the access password for a session Bearer token |
| `POST` | `/api/connect` | Provide Gmail credentials and start a scan |
| `GET` | `/api/progress` | Poll scan progress (processed / total / current log line) |
| `GET` | `/api/report` | Fetch the full analysis report for the current user |
| `POST` | `/api/subscriptions/add` | Add a manual subscription entry |
| `GET` | `/api/health-score` | Get per-merchant health scores |
| `GET` | `/api/cancellation` | Get cancellation links for all subscriptions |
| `POST` | `/api/cancellation/mark` | Mark or unmark a subscription for cancellation |
| `GET` | `/api/alerts/config` | Get the current Telegram alert configuration |
| `POST` | `/api/alerts/config` | Save Telegram bot token and chat ID |
| `POST` | `/api/alerts/test` | Send a test Telegram message |

Interactive API docs are available at `http://localhost:8000/docs` when the server is running.

---

## Multi-User Data Isolation

SubTrack is designed so multiple people can use the same instance without seeing each other's data.

- When a user enters their Gmail credentials, the server binds their session token to their email address
- All data (parsed subscriptions, the report, alert configs, sent-alert history) is stored in `data/{hash}/` where `{hash}` is the first 16 characters of the MD5 of the user's email address
- No user can ever read, overwrite, or interfere with another user's data
- Session tokens are persisted to `data/tokens.json` so users stay logged in across server restarts

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `IMAP authentication failed` | Verify App Password is correct; ensure 2FA is enabled |
| `Missing GMAIL_ADDRESS…` | Check that `.env` exists and has both variables set |
| `No records found` | Try expanding `LOOKBACK_DAYS`; ensure IMAP is enabled in Gmail settings |
| Dashboard shows no data | Run the parser first (Step 2) or place an existing `subscriptions.jsonl` in the same directory |
| Problem | Fix |
|---|---|
| **"Failed to connect"** after entering credentials | Your session token may be stale. Hard-refresh the page (Ctrl+Shift+R / Cmd+Shift+R) and try again. The app will fetch a fresh token automatically. |
| **IMAP authentication failed** | Double-check the App Password — it must be the 16-character code, not your regular Google password. Make sure 2-Step Verification is still enabled. |
| **No subscriptions found** | Ensure IMAP is enabled in Gmail: Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP |
| **ngrok ERR_NGROK_8012** | You started ngrok pointing at the wrong port. Make sure you run `ngrok http --url=... 8000`, not port 80. |
| **Old version showing after git pull** | The `frontend/dist/` build is not pushed to Git. After pulling, rebuild with `cd frontend && npm install && npm run build && cd ..` |
| **lightningcss error on Intel Mac / Linux** | Node modules built on one architecture don't work on another. Run `rm -rf frontend/node_modules && cd frontend && npm install && npm run build` |
| **Telegram test message fails** | Verify the bot token is correct and that you have started a conversation with the bot (send it `/start` in Telegram first) |
| **"uvicorn: command not found"** | Use `python -m uvicorn` instead of calling the binary directly |
| **Page resets to step 1 on reload** | This is fixed in the latest version. Pull the latest code and rebuild the frontend. |

---

## Security Notes

- SubTrack uses Gmail's **IMAP protocol in read-only mode** — it never sends, deletes, moves, or modifies any email
- Your Gmail App Password is stored only in the per-user config file on the host machine (`data/{hash}/alerts_config.json`) and is never logged or transmitted elsewhere
- Session tokens are random 256-bit URL-safe strings generated with Python's `secrets` module
- All `/api/*` routes are protected by Bearer token middleware — unauthenticated requests receive a 401 immediately
- If you're sharing the app with others, set a strong `ACCESS_PASSWORD` so only invited users can create sessions

---

## License

To enable IMAP in Gmail:
`Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP`
MIT — do whatever you want with it.
