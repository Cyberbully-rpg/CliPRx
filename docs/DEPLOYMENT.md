# Deployment: Render (backend) + Vercel (frontend)

Both free tiers, both connected to the `Cyberbully-rpg/CliPRx` GitHub repo so pushes to `main` auto-deploy.

## 1. Backend → Render

1. Sign in at https://render.com (GitHub login is simplest — it also grants Render repo access).
2. **New +** → **Web Service** → connect the `CliPRx` repo.
3. Settings:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
4. **Environment** tab — add these (copy the values from your local `backend/.env`):
   - `GEMINI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `ALLOWED_ORIGINS` — set to `*` for the first deploy; tighten to the real Vercel URL after step 2 below (comma-separated if you need more than one, e.g. `https://cliprx.vercel.app,http://localhost:3000`)
5. Create Web Service. First deploy takes a few minutes (installs scikit-learn/pandas/reportlab). Note the resulting URL, e.g. `https://cliprx-api.onrender.com`.
6. **Free-tier note**: the service spins down after 15 minutes idle. The next request wakes it — expect ~30–50s before the first response, after which it's fast again. `GET /health` is a safe endpoint to ping if you want to keep it warm (e.g. an external uptime pinger), matching the code comment `Render/UptimeRobot keepalive target`.

## 2. Frontend → Vercel

From the repo root:

```bash
npm i -g vercel        # if not already installed
vercel login           # interactive browser login — do this yourself
cd frontend
vercel link             # first time: creates/links the Vercel project
vercel env add NEXT_PUBLIC_API_BASE_URL production   # paste the Render URL from step 1
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
vercel --prod
```

The final command prints the live `https://<project>.vercel.app` URL.

Repeat `vercel env add ... preview` and `... development` too if you want the same values for preview deploys / `vercel dev`.

## 3. Close the loop

Go back to Render → Environment → set `ALLOWED_ORIGINS` to the Vercel URL from step 2 (plus `http://localhost:3000` if you still want local dev to work against the deployed backend). Render redeploys automatically on env var save.

## 4. Verify

Open the Vercel URL, sign up, confirm the email, log in, upload a sample CSV from `data/samples/`, declare tiers, run the analysis, view the ranked report, download the PDF, delete the report. A CORS error at this point means step 3 hasn't been done yet (or hasn't finished redeploying) — check the browser console.
