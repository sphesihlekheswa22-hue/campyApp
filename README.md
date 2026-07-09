# JSE Analytics Platform

Production-ready SaaS for JSE annual report analytics, governance analysis, and financial benchmarking.

## Tech Stack

- **Backend:** Python FastAPI, SQLAlchemy, PostgreSQL, Alembic, JWT, RBAC
- **Frontend:** Vanilla HTML (Jinja2 templates), Tailwind CSS, JavaScript, Chart.js
- **Storage:** Local disk or S3-compatible (Cloudflare R2, AWS S3)
- **Jobs:** Database-backed queue with background worker + APScheduler
- **Extraction:** pdfplumber, optional Camelot, OCR, optional OpenAI LLM assist
- **Email:** Brevo API (production) or MailHog (dev)

## Quick Start (Docker)

```bash
cp .env.example .env
docker-compose up --build
```

Open http://localhost:8000

### Default Platform Owner

- Email: `admin@bluemachines.com`
- Password: set via `PLATFORM_OWNER_PASSWORD` in `.env`

## Production (Render + Neon + R2)

1. Push to GitHub
2. Neon PostgreSQL → `DATABASE_URL`
3. Cloudflare R2 bucket → set `STORAGE_BACKEND=s3`, `S3_*` vars
4. Brevo API key → `BREVO_API_KEY`
5. Set `APP_URL` to your Render URL
6. Deploy via `render.yaml` blueprint

Run migrations on deploy: `alembic upgrade head` (in `start.sh`)

## Features

| Feature | Description |
|---------|-------------|
| Report upload & extraction | PDF → financials + governance, auto analytics |
| Report detail page | Per-report financials, governance, retry, PDF download |
| S3/R2 storage | PDFs survive Render redeploys |
| Job queue | Reliable extraction via `background_jobs` table |
| Notifications | In-app alerts for extraction, uploads, health |
| Compliance checklist | King IV + JSE Listings mapping |
| JSE metadata | JSE code, sector, listing date, market cap on companies |
| Scheduled emails | Monthly analytics summary (Settings) |
| Invite flow | Temp password + force change on first login |
| API pagination | Users, companies, reports return `{ items, total }` |
| Health alerts | Email platform owner when extractions backlog |

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `/api/auth` | Login, password change, reset |
| `/api/users` | Admin-created users, invite emails |
| `/api/companies` | CRUD with JSE metadata |
| `/api/reports` | Upload, download (S3/local), paginated list |
| `/api/extractions` | Results, summary, retry via job queue |
| `/api/analytics` | Scores, benchmarking, PDF/Excel export |
| `/api/governance` | Narratives + `/compliance` checklist |
| `/api/notifications` | In-app notification feed |
| `/api/scheduled-reports` | Monthly email schedules |
| `/api/audit` | Audit logs (platform owner) |

## User Roles

1. **Platform Owner** — Companies, users, view all data, audit, health (no report upload)
2. **Company Admin** — Upload reports, team, analytics, scheduled emails
3. **Employee** — Read-only company data

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -q
```

## License

Proprietary — campyApp
