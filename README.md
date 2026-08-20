# CliPRx — Cloud Infrastructure Prescriber

Turns a cloud billing CSV export into a ranked list of specific, effort-weighted
cost-optimization actions — not a dashboard, a prescription: which service, what to
do about it, how much it saves, how many engineering hours it takes, and whether
it's safe to touch.

Built on the **DIPPA framework** (Data Ingestion → Intelligent Preprocessing →
Predictive Modeling → Performance Analytics → Actionable Insights), as specified in
`CliPRx_PRD_v2.0_FullProduct.docx` and `CliPRx_TRD_v1.0.docx`.

## Current status: Phase 1 only

This repo currently implements **Phase 1 (Core Pipeline)** from the project
roadmap: multi-cloud CSV parsing, anomaly detection, pattern matching, risk
scoring, conflict resolution, ROI ranking, and Gemini-rendered output — reachable
through a single backend endpoint, with no UI yet.

**Not implemented yet:** authentication, database persistence, report history,
PDF export, and the frontend (Phases 2-5 of the roadmap). See the TRD for the full
intended scope.

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
`cloud_provider` set to `aws`, `azure`, or `gcp` (multipart form: `file` + `cloud_provider`).
`GET /health` is a plain liveness check.

## Generating sample data

```bash
python data/generator.py                    # writes sample_aws.csv, sample_azure.csv, sample_gcp.csv to data/samples/
python data/generator.py --provider aws --rows 300
```

Each generated file mixes ordinary background spend with a handful of intentional
anomalies chosen to trigger real patterns in `backend/patterns/`, so it can be fed
straight into the pipeline and produce actual prescriptions.

## How the pipeline works

Each stage is a pure function; `backend/main.py` wires them together in sequence:

1. **Data Ingestion** — `backend/parsers/{aws,gcp,azure}_parser.py` normalize each
   provider's raw CSV into a common 8-column schema.
2. **Predictive Modeling** — `backend/ml/isolation_forest.py` scores each row's
   anomaly likelihood (0.0-1.0) using an Isolation Forest, falling back to a
   median-multiplier heuristic on very small datasets.
3. **Pattern Matching** — `backend/ml/pattern_matcher.py` matches flagged rows
   against a 30-pattern-per-provider library (`backend/patterns/*.json`) of known
   cost-saving actions.
4. **Risk Assessment** — `backend/ml/failure_scorer.py` estimates failure risk and
   cost per matched service.
5. **Conflict Resolution** — `backend/conflict_resolver.py` applies a three-tier
   safety model so recommendations never suggest touching services the user has
   declared essential.
6. **ROI Ranking** — `backend/roi_ranker.py` ranks surviving recommendations by
   estimated savings per engineering hour, risk-adjusted.
7. **Actionable Insights** — `backend/services/gemini_service.py` renders each
   ranked recommendation as a plain-language sprint ticket via the Gemini API.

See `CLAUDE.md` for a more detailed technical walkthrough of each stage.

## Tech stack (Phase 1)

- **Backend:** FastAPI (Python 3.11)
- **ML:** scikit-learn (Isolation Forest)
- **LLM:** Google Gemini
- **Data:** pandas

## Repo layout

```
backend/
  main.py                FastAPI entry point
  parsers/                AWS, Azure, GCP CSV normalizers
  ml/                     Isolation Forest, pattern matcher, failure scorer
  patterns/                30-pattern JSON library per cloud provider
  services/               Gemini integration
  conflict_resolver.py
  roi_ranker.py
  db/migrations/          Supabase client (not yet wired into the pipeline)
data/
  generator.py            Synthetic billing CSV generator
  samples/                Generated + hand-written sample CSVs
test.py                   Pipeline smoke test (small built-in mock CSV)
```
