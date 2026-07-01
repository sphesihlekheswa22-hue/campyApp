# JSE Analytics Platform

Production-ready SaaS for JSE annual report analytics, governance analysis, and financial benchmarking.

## Tech Stack

- **Backend:** Python FastAPI, SQLAlchemy, PostgreSQL, Alembic, JWT, RBAC
- **Frontend:** Vanilla HTML (Jinja2 templates), Tailwind CSS, JavaScript, Chart.js
- **AI/Data:** pdfplumber, Camelot, Pandas, NumPy, Scikit-Learn
- **Infrastructure:** Docker, PostgreSQL, MailHog (dev email)

## Quick Start (Docker)

```bash
cp .env.example .env
docker-compose up --build
```

Open http://localhost:8000

### Default Platform Owner

- Email: `admin@bluemachines.com`
- Password: `Admin123!`

### Dev Email (MailHog)

- SMTP: localhost:1025
- Web UI: http://localhost:8025

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `/api/auth` | Registration, login, PIN confirmation, password reset |
| `/api/users` | User management, profile |
| `/api/companies` | Company CRUD, logos |
| `/api/reports` | PDF upload, download |
| `/api/extractions` | Extraction results, retry |
| `/api/analytics` | Trends, scores, risk, benchmarking, exports |
| `/api/governance` | Governance narratives |
| `/api/audit` | Audit logs (platform owner) |

## User Roles

1. **Platform Owner** — All companies, subscriptions, audit logs, system health
2. **Company Admin** — Company users, reports, analytics, governance
3. **Employee** — View assigned company data, limited exports

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

For Docker/self-hosted:

1. Set strong `JWT_SECRET` and database credentials in `.env`
2. Use HTTPS reverse proxy (nginx/Caddy) in front of FastAPI
3. Run `docker-compose up -d` with production env vars
4. Configure real SMTP credentials for email delivery
5. Set up PostgreSQL backups for `postgres_data` volume
6. Mount persistent volume for `uploads/`

## Project Structure

```
CompanyApp/
├── backend/          # FastAPI application
├── frontend/
│   ├── templates/    # Jinja2 HTML (extends base.html)
│   ├── css/
│   └── js/
├── docker-compose.yml
└── .env.example
```

## Features

- JWT access & refresh tokens with bcrypt password hashing
- Admin/Company/Employee registration with PIN activation
- PDF extraction pipeline (financials + governance narratives)
- Analytics engine (trends, scoring, ML risk classification)
- Benchmarking and company comparison
- PDF and Excel report exports
- Audit logging on all mutations
- Role-based dashboards and navigation
- Dark mode responsive UI
