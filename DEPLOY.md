# Deploy guide (Render + Vercel)

## 0) Supabase Postgres (recommended)

Create a Supabase project and copy the **Session pooler** connection string:

`postgresql+psycopg2://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres?sslmode=require`

For serverless workloads, use Transaction pooler (port `6543`).

Environment files supported by this backend:

- `backend/.env`
- `backend/.env.local`
- `backend/.env.staging`
- `backend/.env.production`

The loader uses `ENV` (default: `local`) and loads:

1. `.env`
2. `.env.{ENV}` (override)

Never commit real credentials.

## 1) Backend FastAPI on Render

- Connect this repository on Render and create a `Web Service`.
- Use:
  - Build command: `pip install -r requirements.txt`
  - Start command: `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`
- Configure environment variables in Render:
  - `DATABASE_URL` (Supabase pooler URL or Render Postgres URL)
  - `JWT_SECRET`
  - `APP_BASE_URL` (URL do frontend para gerar links de convite, ex.: `https://seu-app.vercel.app`)
  - `INVITE_TOKEN_SECRET`
  - `INVITE_EXPIRY_HOURS` (ex.: `168`)
  - `CORS_ORIGINS`
  - `CORS_ORIGIN_REGEX` (optional, for Vercel previews)
  - `CORS_ALLOW_ALL=false`

This repo also includes `backend/render.yaml` with the same setup.

Create a Render Postgres database first, then copy its `External Database URL`
into `DATABASE_URL` in the Web Service.

If using Supabase, run migrations against Supabase before first deploy:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://...sslmode=require"
alembic upgrade head
```

## 2) CORS configuration

`backend/main.py` reads these variables:

- `CORS_ORIGINS`: comma-separated allowlist.
- `CORS_ORIGIN_REGEX`: optional regex for preview URLs.
- `CORS_ALLOW_ALL`: keep `false` in production.

Example:

```env
CORS_ORIGINS=https://your-project.vercel.app,http://localhost:50000
CORS_ORIGIN_REGEX=https://your-project(-git-.*)?\.vercel\.app
CORS_ALLOW_ALL=false
```

## 3) Flutter Web on Vercel

- If you use this workspace as a monorepo, set Vercel project root to `apr_app`.
- This workspace includes:
  - `apr_app/vercel.json`
  - `apr_app/scripts/vercel_build.sh`
- `vercel_build.sh` downloads Flutter in CI and runs:
  - `flutter pub get`
  - `flutter build web --release --dart-define=API_BASE_URL=...`

Set environment variables in Vercel:

- `API_BASE_URL=https://<your-backend>.onrender.com`
- `SUPABASE_URL` (optional)
- `SUPABASE_ANON_KEY` (optional)

Output directory is `build/web`.
`apr_app/vercel.json` também já inclui rewrite de `/invite` para `index.html`.

## 4) Backend validation after Render deploy

Run from PowerShell:

```powershell
./scripts/smoke_test.ps1 -BaseUrl https://<your-backend>.onrender.com
```

If you already have valid credentials:

```powershell
./scripts/smoke_test.ps1 `
  -BaseUrl https://<your-backend>.onrender.com `
  -Email admin@example.com `
  -Password "your-password"
```

This validates `/health`, `/v1/health`, `/docs`, and auth/APR routes.

## 5) Frontend go/no-go

On the Vercel URL:

1. Open app in a clean browser session and confirm it lands on Login.
2. Login and confirm the app opens `MainShell` on APR tab.
3. Press F5 and confirm session persists and still opens in APR.
4. Open DevTools Network and confirm APR/API calls return without CORS preflight failure.
