# MRABILITY Finance Pvt Ltd

A fintech loan aggregator that connects you with multiple banks and NBFCs across India.

## Local Development

```bash
cd mrability_finance
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python server.py
```

Open http://localhost:8080

**Admin Login:** admin@mrability.in / Admin@1234

> Locally the app uses **SQLite** — no database setup needed.

---

## Deploy to Railway (Recommended)

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Select your repo
4. Add a **PostgreSQL** plugin (click "+ New" → "Database" → "PostgreSQL")
5. Railway auto-sets `DATABASE_URL` — the app detects it and uses PostgreSQL
6. Set environment variables (Settings → Variables):
   - `SECRET_KEY` — any random strong string
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — (optional, for Google login)
7. Deploy — Railway auto-detects `Procfile` and starts Gunicorn

**Your site will be live at:** `https://your-app.up.railway.app`

---

## Deploy to Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New** → **Web Service**
3. Connect your repo
4. Render detects `render.yaml` — creates both the web service and PostgreSQL database
5. Set environment variables in the Render dashboard:
   - `SECRET_KEY` — any random strong string
6. Deploy

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Auto-set by Railway/Render | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing secret |
| `PORT` | Auto-set | Server port (default: 8080) |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth client secret |
| `FACEBOOK_APP_ID` | Optional | Facebook OAuth app ID |
| `FACEBOOK_APP_SECRET` | Optional | Facebook OAuth secret |
| `TWILIO_ACCOUNT_SID` | Optional | For SMS OTP delivery |
| `TWILIO_AUTH_TOKEN` | Optional | Twilio auth token |
| `TWILIO_FROM_NUMBER` | Optional | Twilio phone number |
| `SMTP_HOST` | Optional | Email server (default: smtp.gmail.com) |
| `SMTP_USER` | Optional | Email username |
| `SMTP_PASSWORD` | Optional | Email password |

---

## Architecture

- **Frontend:** HTML5 + CSS3 + Vanilla JS (no framework)
- **Backend:** Flask (Python)
- **Database:** PostgreSQL (production) / SQLite (local dev)
- **Auth:** JWT tokens + bcrypt password hashing
- **Server:** Gunicorn (production) / Flask dev server (local)
