# CliPRx — Cloud Infrastructure Prescriber

[![CI](https://github.com/Cyberbully-rpg/CliPRx/actions/workflows/ci.yml/badge.svg)](https://github.com/Cyberbully-rpg/CliPRx/actions/workflows/ci.yml)

Turns a cloud billing CSV export into a ranked list of specific, effort-weighted
cost-optimization actions — not a dashboard, a prescription: which service, what to
do about it, how much it saves, how many engineering hours it takes, and whether
it's safe to touch.

Built on the **DIPPA framework** (Data Ingestion → Intelligent Preprocessing →
Predictive Modeling → Performance Analytics → Actionable Insights), as specified in
`CliPRx_PRD_v2.0_FullProduct.docx` and `CliPRx_TRD_v1.0.docx`.

## Current status: Phase 1-3 complete

- **Phase 1 (Core Pipeline):** multi-cloud CSV parsing, anomaly detection, pattern
  matching, risk scoring, conflict resolution, ROI ranking, and Gemini-rendered
  output.
- **Phase 2 (Persistence):** the full multi-step upload → declare tiers → run
  pipeline → reports flow, plus PDF export — with row-level security and
  per-request ownership checks.
- **Phase 3 (Frontend):** a Next.js app in `frontend/` — a marketing landing
  page plus the dashboard (upload, tier declaration, pipeline run, report
  list/detail, sprint tickets, PDF download).

**Single-tenant.** There is no login or signup: the app runs as one fixed
identity (`DEFAULT_USER_ID`, a real Supabase Auth user the backend falls back to
when a request carries no JWT). The auth machinery is still there and still
verifies a real `Authorization: Bearer` token if one is sent — it's just not
required. Note this means a deployed backend is open to anyone with its URL.

See `CLAUDE.md` for the full technical walkthrough of every stage and
`docs/DEPLOYMENT.md` for deploying both halves (Render + Vercel, both free tier).

## Quick start

```bash
python -m venv venv
venv\Scripts\activate          # or `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

cp backend/.env.example backend/.env
# then fill in GEMINI_API_KEY in backend/.env

python test.py                 # runs the pipeline against a small built-in mock CSV
```

To run the API server:

```bash
cd backend
uvicorn main:app --reload
```

Then `POST` a CSV to `http://localhost:8000/api/v1/test-pipeline` with
`cloud_provider` set to `aws`, `azure`, `gcp`, or `focus` (multipart form:
`file` + `cloud_provider`). `GET /health` is a plain liveness check.

`focus` accepts a [FOCUS 1.0](https://focus.finops.org/) export — a vendor-neutral
billing schema that can describe several clouds in one file. Those rows are routed
to the matching provider's pattern library per row via the export's own
`ProviderName` column.

To run the frontend against it:

```bash
cd frontend
cp .env.local.example .env.local   # only needs NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev                        # http://localhost:3000
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest                             # 86 tests, ~6s, no network or API keys needed
```

`tests/` covers the pure stages of the pipeline: the normalized 8-column schema
each provider parser must emit (including the awkward real-world cases — comma-
and `$`-formatted costs, exports carrying two candidate columns for the same
field, GCP reports where a USD and an INR cost column sit side by side), the
anomaly scorer, the pattern matcher's cross-service guard, the risk heuristics,
the three-tier conflict model, and ROI ranking — plus one end-to-end chain
asserting that a tier-1 service is dropped entirely while a tier-2 core
modification survives flagged and ranked last.

`python test.py` is a separate manual smoke script that runs the whole chain
including the live Gemini call, so it needs `GEMINI_API_KEY`.

CI (`.github/workflows/ci.yml`) runs the suite plus a frontend typecheck and
production build on every push and pull request.

## Generating sample data

```bash
python data/generator.py                    # writes sample_{aws,azure,gcp,focus}.csv to data/samples/
python data/generator.py --provider aws --rows 300
```

Each generated file mixes ordinary background spend with a handful of intentional
anomalies chosen to trigger real patterns in `backend/patterns/`, so it can be fed
straight into the pipeline and produce actual prescriptions. `sample_focus.csv`
additionally spans all three providers in one file and includes a row from a
provider CliPRx has no patterns for, to exercise the upload-warning path.

## How the pipeline works

Each stage is a pure function; `backend/main.py` wires them together in sequence:

1. **Data Ingestion** — `backend/parsers/{aws,gcp,azure,focus}_parser.py` normalize
   each provider's raw CSV into a common 8-column schema.
2. **Predictive Modeling** — `backend/ml/isolation_forest.py` scores each row's
   anomaly likelihood (0.0-1.0) using an Isolation Forest, falling back to a
   median-multiplier heuristic on very small datasets.
3. **Pattern Matching** — `backend/ml/pattern_matcher.py` matches flagged rows
   against a ~35-pattern-per-provider library (`backend/patterns/*.json`) of known
   cost-saving actions.
4. **Risk Assessment** — `backend/ml/failure_scorer.py` estimates failure risk and
   cost per matched service.
5. **Conflict Resolution** — `backend/conflict_resolver.py` applies a three-tier
   safety model so recommendations never suggest touching services the user has
   declared essential.
6. **ROI Ranking** — `backend/roi_ranker.py` ranks surviving recommendations by
   estimated savings per engineering hour, risk-adjusted.
7. **Actionable Insights** — `backend/services/gemini_service.py` renders each
   ranked recommendation as a plain-language sprint ticket via the Gemini API
   (concurrently, with a plain-text fallback on failure). Tickets are stored on
   the report and shown in both the dashboard and the exported PDF.

See `CLAUDE.md` for a more detailed technical walkthrough of each stage.

## Tech stack (Phase 1)

- **Backend:** FastAPI (Python 3.11)
- **ML:** scikit-learn (Isolation Forest)
- **LLM:** Google Gemini
- **Data:** pandas

## Repo layout

```
backend/
  main.py                 FastAPI entry point + legacy one-shot endpoint
  api/                    Upload, pipeline, reports, and auth endpoints
  parsers/                AWS, Azure, GCP, FOCUS CSV normalizers
  ml/                     Isolation Forest, pattern matcher, failure scorer
  patterns/               ~35-pattern JSON library per cloud provider
  services/               Gemini, PDF, persistence, ingest, ownership
  conflict_resolver.py
  roi_ranker.py
  db/migrations/          Supabase client factory
frontend/                 Next.js dashboard + landing page
supabase/migrations/      Database schema (SQL)
data/
  generator.py            Synthetic billing CSV generator
  samples/                Generated + hand-written sample CSVs
tests/                    pytest suite (parsers, pipeline stages, ingestion)
test.py                   Manual end-to-end smoke script (includes the Gemini call)
```
