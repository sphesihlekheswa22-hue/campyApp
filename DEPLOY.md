# Deploy: Render + Neon PostgreSQL

This guide deploys **JSE Analytics** to [Render](https://render.com) with a [Neon](https://neon.tech) Postgres database.

## 1. Push code to GitHub

If the repo is not on GitHub yet:

1. Create a new repository at https://github.com/new (name e.g. `CompanyApp` or `jse-analytics`)
2. **Do not** initialize with README (this project already has one)
3. Push from your machine:

```powershell
cd "c:\Users\Zoey\OneDrive\Documents\My Web Apps\CompanyApp"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

## 2. Create Neon database

1. Sign in at https://console.neon.tech
2. **New Project** → choose a region close to your users (e.g. AWS Europe)
3. Copy the **connection string** (pooled recommended for Render):
   - Format: `postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`
4. Neon also accepts `postgres://` — the app normalizes it automatically.

## 3. Deploy on Render

### Option A — Blueprint (recommended)

1. Go to https://dashboard.render.com/blueprints
2. **New Blueprint Instance** → connect your GitHub repo
3. Render reads `render.yaml` and creates the web service
4. When prompted, set **sync: false** env vars:
   - `DATABASE_URL` — paste your Neon connection string
   - `PLATFORM_OWNER_PASSWORD` — strong password for `admin@bluemachines.com`
   - (Optional) SMTP vars if you want real email

### Option B — Manual web service

| Setting | Value |
|---------|--------|
| Root Directory | `backend` |
| Build Command | `bash scripts/render-build.sh` |
| Start Command | `bash scripts/start.sh` |
| Health Check | `/api/health` |

**Environment variables:**

| Key | Value |
|-----|--------|
| `APP_ENV` | `production` |
| `DATABASE_URL` | Neon connection string |
| `JWT_SECRET` | long random string (Render can generate) |
| `PLATFORM_OWNER_EMAIL` | `admin@bluemachines.com` |
| `PLATFORM_OWNER_PASSWORD` | your admin password |

## 4. First deploy

On each deploy, Render runs:

1. `pip install -r requirements-render.txt`
2. `npm ci && npm run build:css` (Tailwind)
3. `alembic upgrade head` (migrations)
4. `python -m app.seed` (demo data — skips if DB already seeded)
5. `uvicorn` on `$PORT`

When deploy succeeds, open your Render URL (e.g. `https://jse-analytics.onrender.com`).

### Login (after seed)

| Role | Email | Password |
|------|-------|----------|
| Platform owner | `admin@bluemachines.com` | value of `PLATFORM_OWNER_PASSWORD` |
| Company admin | `admin@bluemachines.co.za` | `Password123!` |

## Notes

- **Free tier:** Render spins down after inactivity; first request may take ~30s.
- **Uploads:** Files on Render’s disk are **ephemeral** (lost on redeploy). Use object storage (S3/R2) for production PDFs.
- **PDF tables:** Render uses `requirements-render.txt` (no Camelot/OpenCV). Text extraction via pdfplumber still works.
- **Reseed:** Run locally against Neon: `DATABASE_URL=... python -m app.seed --reset` (careful — wipes data).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on npm | Ensure `frontend/package-lock.json` is committed |
| DB connection error | Check Neon string includes `sslmode=require` |
| 502 on first load | Wait for cold start; check Render logs |
| Migrations fail | Verify `DATABASE_URL` user can create tables |
