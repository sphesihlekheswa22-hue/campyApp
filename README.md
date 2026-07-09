# JSE Analytics Platform

Production-ready SaaS for JSE annual report analytics, governance analysis, and financial benchmarking.

## Tech Stack

- **Backend:** Python FastAPI, SQLAlchemy, PostgreSQL, Alembic, JWT, RBAC
- **Frontend:** Vanilla HTML (Jinja2 templates), Tailwind CSS, JavaScript, Chart.js
- **Data extraction:** pdfplumber, Camelot, Pandas — rule-based analytics scoring
- **Infrastructure:** Docker, PostgreSQL; Render + Neon for production

## Quick Start (Docker)

```bash
cp .env.example .env
docker-compose up --build
```

Open http://localhost:8000

### Default Platform Owner

- Email: `admin@bluemachines.com`
- Password: set via `PLATFORM_OWNER_PASSWORD` in `.env` (default `Admin123!` in dev)

### Dev Email (MailHog)

- SMTP: localhost:1025
- Web UI: http://localhost:8025

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `/api/auth` | Login, PIN confirmation, password reset |
| `/api/users` | Admin-created users, profile |
| `/api/companies` | Company CRUD, logos |
| `/api/reports` | PDF upload (company admin), download, detail |
| `/api/extractions` | Extraction results, summary, retry |
| `/api/analytics` | Trends, scores, risk, benchmarking, exports |
| `/api/governance` | Governance narratives |
| `/api/audit` | Audit logs (platform owner) |

## User Roles

1. **Platform Owner** — Manage companies and users, view all data, audit logs, system health. Does not upload reports.
2. **Company Admin** — Upload reports, run analysis, manage team, view analytics and governance.
3. **Employee** — View assigned company data (read-only; no exports).

Users are created by admins only — there is no public self-registration.

## Typical workflow

1. Platform owner creates a company and company admin.
2. Company admin uploads a PDF annual report (optional FY year tag).
3. Extraction runs automatically; analytics runs when extraction completes.
4. View scores on Dashboard, Analytics, Governance, and per-report detail pages.

## Local Development (without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
# Start PostgreSQL and set DATABASE_URL in .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

### Frontend

Served automatically by FastAPI from `frontend/templates/` using Jinja2 (`base.html` layout inheritance).

## Production Deployment

See **[DEPLOY.md](DEPLOY.md)** for Render + Neon step-by-step instructions.

Quick summary:

1. Push this repo to GitHub
2. Create a Neon PostgreSQL project and copy `DATABASE_URL`
3. Connect the repo on Render (Blueprint uses `render.yaml`)
4. Set `DATABASE_URL`, `JWT_SECRET`, and `PLATFORM_OWNER_PASSWORD` in Render env vars

**Note:** Render free tier uses ephemeral disk — uploaded PDFs are lost on redeploy. Use S3/R2 or persistent disk for production file storage.

For Docker/self-hosted:

1. Set strong `JWT_SECRET` and database credentials in `.env`
2. Run migrations and seed: `alembic upgrade head && python -m app.seed`
3. Serve with `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Project Structure

```
backend/app/          # FastAPI app, routers, models, extraction, analytics
frontend/templates/   # Jinja2 HTML pages
frontend/js/          # API client, auth, layout, utilities
```

## License

Proprietary — Blue Machines / campyApp
