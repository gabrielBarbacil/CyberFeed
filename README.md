# CyberFeed 🛡️

> Real-time cybersecurity news and critical CVE aggregator.
> Built with FastAPI, NVD API, and RSS feeds.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- 🔴 **Critical & High CVEs** — pulled directly from NVD (NIST) API v2
- 📰 **Security News** — aggregated from 5 RSS feeds in real time
- 🔍 **Search & Filter** — by type, severity, or keyword
- ♻️ **Auto-refresh** — configurable interval (default: 60 minutes)
- 📊 **Stats dashboard** — critical/high CVE count and daily news

---

## Sources

**CVEs:** National Vulnerability Database (NIST) — CVSS >= 7.0

**News:**
- The Hacker News
- BleepingComputer
- Krebs on Security
- SecurityWeek
- CISA Advisories

---

## Tech Stack

- **Backend:** Python 3.11 + FastAPI + APScheduler
- **Data:** NVD API v2 + feedparser (RSS)
- **Frontend:** Vanilla JS + custom CSS
- **Deploy:** Railway (Procfile included)

---

## Project Structure

```
cyberfeed/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI routes, scheduler, cache
│   └── fetchers/
│       ├── __init__.py
│       ├── cve_fetcher.py       # NVD API v2 client
│       └── news_fetcher.py      # RSS feed parser
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/
│   └── index.html
├── .env.example                 # Environment variables template
├── .gitignore
├── Procfile                     # Railway deploy config
└── requirements.txt
```

---

## Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/gabrielBarbacil/cyberfeed
cd cyberfeed

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your NVD API key (optional but recommended)

# 5. Run
uvicorn app.main:app --reload
```

Open in browser: `http://localhost:8000`

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `NVD_API_KEY` | NVD API key (free) | None |
| `CVE_DAYS_BACK` | Days back to search CVEs | 7 |
| `REFRESH_INTERVAL` | Auto-refresh interval (minutes) | 60 |

Get a free NVD API key at: https://nvd.nist.gov/developers/request-an-api-key

Without key: 5 req/30s — With key: 50 req/30s

---

## Deploy on Railway

1. Push project to GitHub
2. Railway → **New Project → Deploy from GitHub repo**
3. Railway auto-detects the `Procfile`
4. Add environment variables in Railway dashboard:
   - `NVD_API_KEY`
   - `CVE_DAYS_BACK` (optional)
   - `REFRESH_INTERVAL` (optional)
5. Deploy — Railway assigns a public URL automatically

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Frontend |
| `/api/feed` | GET | Full feed (params: type, severity, q) |
| `/api/stats` | GET | Stats only |
| `/api/refresh` | GET | Force cache refresh (rate limited: 5/min) |

---

## Security

- XSS protection via HTML escaping on all rendered fields
- URL validation to prevent javascript: injection
- Rate limiting on refresh endpoint (5 req/min)
- NVD API key stored in environment variables only
- No database — in-memory cache only

---

## Author

**Gabriel Barbacil**
- GitHub: [@gabrielBarbacil](https://github.com/gabrielBarbacil)
- LinkedIn: [gabrielbarbacil](https://www.linkedin.com/in/gabrielbarbacil/)

---

## License

MIT — free to use, modify and distribute.
