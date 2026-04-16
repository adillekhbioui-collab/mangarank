# Deployment Guide (GitHub + DigitalOcean + Vercel)

This guide deploys ManhwaRank: The Archive with a DigitalOcean backend and a Vercel frontend.

## Stack

- Code hosting and CI: GitHub
- Backend (FastAPI): DigitalOcean Droplet
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

## 2. Backend Deploy on DigitalOcean

1. Create a Droplet and point DNS:
   - `api.manhwarank.me` -> Droplet public IP
2. Clone and install on the Droplet:
   - `git clone https://github.com/adillekhbioui-collab/mangarank.git /opt/manhwa`
   - `cd /opt/manhwa`
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Create `/opt/manhwa/.env` with production values:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_JWT_SECRET`
   - `ALLOWED_ORIGINS=https://manhwarank.me,https://www.manhwarank.me,https://manhwa-rank.vercel.app`
4. Run backend via systemd (`manhwa-api.service`) and reverse-proxy with Nginx.
5. Issue SSL for API domain:
   - `certbot --nginx -d api.manhwarank.me --redirect`

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
   - `VITE_API_BASE_URL` = `https://api.manhwarank.me`
   - `VITE_UMAMI_SHARE_URL` = your Umami share URL
6. Deploy.

Example:
- `VITE_API_BASE_URL=https://api.manhwarank.me`

## 4. Verify Endpoints

After both are live:

1. Open backend health check manually:
   - `https://api.manhwarank.me/docs`
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

- Vercel free has monthly build/runtime limits.
- Supabase free has storage and request limits.

This is normal for MVP and early traffic.

## 8. Release Workflow (recommended)

1. Work in feature branch.
2. Open PR to `main`.
3. Let GitHub Actions pass.
4. Merge to `main`.
5. Vercel auto-deploys from GitHub.
6. Backend deploy can be manual (`git pull` + `systemctl restart manhwa-api`) or automated with a GitHub Actions SSH deploy.

## 9. Optional: Custom Domain (still free on Vercel)

- Add custom domain in Vercel project settings.
- Keep frontend on `manhwarank.me` and backend on `api.manhwarank.me`.
