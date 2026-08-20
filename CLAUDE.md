# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CliPRx is a Phase 1 backend that ingests cloud billing CSV exports (AWS/Azure/GCP), runs them through an ML + rules pipeline, and returns ranked, LLM-authored "sprint ticket" cost-optimization prescriptions. It is a FastAPI service backed by Supabase (Postgres) and Google Gemini.

## Commands

There is no frontend, no test framework, and no linter configured — verification is done by running the pipeline end to end.

```bash
# One-time setup: installs deps from the root requirements.txt, then runs the pipeline test
python setup.py

# Run the FastAPI server (must run from backend/, since backend/main.py uses bare imports like `from parsers... import`)
cd backend
uvicorn main:app --reload

# Run the pipeline against a hardcoded mock CSV, without the HTTP layer (run from repo root)
python test.py
```

`test.py` is the closest thing to a test suite: it feeds a small mock AWS CSV through every pipeline stage and prints the final Gemini-rendered tickets. When changing any pipeline stage, run it to sanity-check the full chain still produces output.

**Gotcha:** both `requirements.txt` (root) and `backend/requirements.txt` are UTF-16LE encoded, not UTF-8. `pip install -r requirements.txt` still works on Windows, but don't naively `cat`/`Read`/edit these files expecting UTF-8 — they render as space-separated characters. The two files are near-duplicates but not identical (root has `nodeenv`/`pyright`, `backend/requirements.txt` doesn't); keep that in mind if dependencies drift between them.

**Import style mismatch:** `backend/main.py` imports its own siblings with bare paths (`from parsers.aws_parser import ...`), which only resolves when the working directory/root is `backend/` (see `backend/pyrightconfig.json`'s `extraPaths: ["."]`). `test.py` instead imports via `from backend.parsers... import ...` from the repo root. Match the import style to whichever entry point you're adding code for.

### Environment variables

Loaded from `backend/.env` (gitignored). Required:
- `GEMINI_API_KEY` — used by `backend/services/gemini_service.py` to render sprint tickets. Required or the `/api/v1/test-pipeline` endpoint fails outright (`test.py` also refuses to run without it).
- `SUPABASE_URL`, `SUPABASE_KEY` — used by `backend/db/migrations/supabase_client.py`. Not yet wired into `main.py`'s pipeline.
- `ANOMALY_THRESHOLD` — optional, defaults to `0.65` in `main.py`; controls the isolation-forest cutoff for flagging a billing row as anomalous.

## Architecture: the DIPPA pipeline

The whole system is one linear pipeline, wired together in `backend/main.py`'s single endpoint (`POST /api/v1/test-pipeline`). Each stage is a pure function that takes the previous stage's output and returns the next; there's no shared state or class hierarchy to trace — read `main.py` top to bottom to see the entire flow, then dive into individual modules.

1. **Data Ingestion** — `backend/parsers/{aws,gcp,azure}_parser.py`. Each `parse_<provider>_csv(bytes) -> pd.DataFrame` normalizes a provider-specific CSV export into the same 8-column schema: `service_name, cost_usd, usage_quantity, usage_type, region, billing_period_start, billing_period_end, tier`. `tier` defaults to `3` (fully mutable) at parse time — nothing currently sets `1` or `2` upstream. Any new provider parser must emit exactly this schema, since every downstream stage assumes it.

2. **Predictive Modeling** — `backend/ml/isolation_forest.py`. Fits an `IsolationForest` (scikit-learn) over `cost_usd`, `usage_quantity`, and a derived `cost_per_unit`, min-max normalizes the anomaly scores to `0.0–1.0` into a new `anomaly_score` column. Datasets under 10 rows skip the model entirely and use a median-multiplier heuristic instead (too few points to fit a meaningful forest).

3. **Pattern Matching** — `backend/ml/pattern_matcher.py`. Filters rows to `anomaly_score >= threshold`, then evaluates each against the provider's JSON pattern library (`backend/patterns/{aws,gcp,azure}_patterns.json`) using simple `equals`/`contains` trigger conditions on a field. A match produces a raw prescription dict with estimated savings range and engineering-hours range pulled straight from the matched pattern. Patterns also carry `immutable_blockers` (e.g. `["tier1"]`, `["tier1","tier2"]`) consumed later by conflict resolution.

4. **Risk Assessment** — `backend/ml/failure_scorer.py`. Computes a rule-based infrastructure `risk_level` (`cost_usd > 500` → High; `tier == 2` → Medium; else Low) and reconciles it against the pattern's own `downtime_risk`, always taking the *higher* of the two (never downgrade a risky action just because the underlying service is cheap). High risk gets a `failure_cost_estimate` of 4x monthly cost.

5. **Conflict Resolution** — `backend/conflict_resolver.py`. Applies the three-tier safety model: `tier == 1` items are dropped entirely (fully immutable — never surfaced); `tier == 2` items whose pattern blocks `tier2` are flagged `is_conflicted` (core service, action modifies it); items that would jump risk from Low baseline to High action risk are also flagged conflicted. Conflicted items survive in the list but are marked, not removed.

6. **ROI Ranking** — `backend/roi_ranker.py`. `roi_score = (avg(savings_min, savings_max) / avg(hours_min, hours_max)) * risk_multiplier`, where `risk_multiplier` is `1.0/0.7/0.4` for Low/Medium/High. Conflicted items are forced to `roi_score = 0.0` so they sort to the bottom rather than being excluded. Output is sorted descending by ROI (savings as tiebreaker) with `rank_position` injected.

7. **Actionable Insights** — `backend/services/gemini_service.py`. Sends each ranked prescription dict to Gemini (`gemini-3.6-flash`) asking for a Jira-style sprint ticket; on any API failure it falls back to a plain-text `"Execute action: {recommended_action}"` string rather than failing the request.

When adding a new pipeline stage or modifying an existing one, preserve the "list of dicts flowing through, each stage adds/mutates keys" contract — nothing here uses typed models (no Pydantic schemas for the prescription objects), so field names are the only contract between stages.

### Adding a new cloud provider

1. Add `backend/parsers/<provider>_parser.py` exporting `parse_<provider>_csv(bytes) -> pd.DataFrame` that emits the standard 8-column schema described above.
2. Add `backend/patterns/<provider>_patterns.json` following the existing pattern schema (`trigger_condition`, `recommended_action`, `savings_range_min_pct`/`max_pct`, `engineering_hours_min`/`max`, `downtime_risk`, `complexity`, `immutable_blockers`).
3. Wire the new branch into the `provider` dispatch in `backend/main.py`.
