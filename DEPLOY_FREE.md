# Free Deployment Guide (GitHub + Render + Vercel)

This guide deploys ManhwaRank: The Archive for free with automatic deploys from GitHub.

## Stack

- Code hosting and CI: GitHub
- Backend (FastAPI): Render (free web service)
- Frontend (React + Vite): Vercel (free)
- Database: Supabase (already in use)

## 1. Push to GitHub

From repository root:

```powershell
git init
git add .
git commit -m "prepare free deployment"
git branch -M main
git remote add origin https://github.com/adillekhbioui-collab/manga-rank.git
git push -u origin main
```

If repo already exists, just commit and push.

## 2. Backend Deploy on Render

1. Open Render dashboard.
2. Click New -> Web Service.
3. Connect your GitHub repo.
4. Configure:
   - Name: manhwarank-backend
   - Environment: Python
   - Root Directory: manhwa-aggregator
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variables:
   - `SUPABASE_URL` = your real Supabase URL
   - `SUPABASE_KEY` = your real Supabase key
6. Deploy.

After deploy, copy backend URL, example:
- `https://manhwarank-backend.onrender.com`

## 3. Frontend Deploy on Vercel

1. Open Vercel dashboard.
2. Click Add New -> Project.
3. Import same GitHub repo.
4. Set project settings:
   - Framework: Vite
   - Root Directory: manhwa-aggregator/frontend
   - Build Command: `npm run build`
   - Output Directory: `dist`
5. Add Environment Variable:
   - `   ` = your Render backend URL (no trailing slash)
6. Deploy.

Example:
- `VITE_API_BASE_URL=https://manhwarank-backend.onrender.com`

## 4. Verify Endpoints

After both are live:

1. Open backend health check manually:
   - `https://<render-url>/stats`
2. Open frontend URL from Vercel.
3. Confirm list and filters load data.

## 5. CORS for Production

Current backend allows all origins. For production hardening:

- Update `backend/main.py` CORS allow_origins to include only your Vercel domain.

Example allowed origin:
- `https://<your-vercel-project>.vercel.app`

## 6. GitHub CI (already added)

Workflow file:
- `.github/workflows/ci.yml`

What it does:
- Backend dependency install + import smoke test
- Frontend dependency install + build

Runs on:
- push to `main` and `dev`
- pull requests to `main`

## 7. Expected Free-Tier Limits

- Render free service may sleep when idle (cold starts).
- Vercel free has monthly build/runtime limits.
- Supabase free has storage and request limits.

This is normal for MVP and early traffic.

## 8. Release Workflow (recommended)

1. Work in feature branch.
2. Open PR to `main`.
3. Let GitHub Actions pass.
4. Merge to `main`.
5. Render and Vercel auto-deploy from GitHub.

## 9. Optional: Custom Domain (still free on Vercel)

- Add custom domain in Vercel project settings.
- If backend is on Render free, keep API domain on Render or move backend later to a provider with free custom-domain-friendly setup.
