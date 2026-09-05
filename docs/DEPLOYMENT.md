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
   - `DEFAULT_USER_ID` — **required.** This app runs single-tenant: there is no login UI, so every request resolves to this one fixed identity (`backend/api/auth.py`). It must be a real Supabase Auth user id, because `uploads`/`reports` carry a foreign key to `auth.users` — see "Single-tenant mode" in `CLAUDE.md` for the one-time command that creates one. Leave it unset and every endpoint returns 401.
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
vercel --prod
```

`NEXT_PUBLIC_API_BASE_URL` is the only variable the frontend needs — it holds no Supabase credentials of its own, since the backend owns every Supabase call.

The final command prints the live `https://<project>.vercel.app` URL.

Repeat `vercel env add ... preview` and `... development` too if you want the same values for preview deploys / `vercel dev`.

## 3. Close the loop

Go back to Render → Environment → set `ALLOWED_ORIGINS` to the Vercel URL from step 2 (plus `http://localhost:3000` if you still want local dev to work against the deployed backend). Render redeploys automatically on env var save.

## 4. Verify

Open the Vercel URL, go to the dashboard, upload a sample CSV from `data/samples/` (try `sample_focus.csv` — it's a multi-provider FOCUS export and also exercises the unrecognized-provider warning), declare tiers, run the analysis, view the ranked report, expand a "Sprint ticket" block, download the PDF, delete the report. There is no sign-up step — the app opens straight into the dashboard.

Two failure modes worth telling apart:
- **CORS error in the browser console** — step 3 hasn't been done yet, or hasn't finished redeploying.
- **Every request returns 401** — `DEFAULT_USER_ID` is unset or isn't a real Supabase Auth user id (step 1.4).

## 5. Note on access

Single-tenant means unauthenticated: anyone who has the Render URL can upload to, read, and delete the default user's reports. There is no per-user separation left to rely on, and no flag that turns the fallback off — the backend still verifies a real `Authorization: Bearer <jwt>` and prefers it, but nothing requires one. Keep the URL private, or put the deployment behind Vercel/Render access controls if that matters for your use.
