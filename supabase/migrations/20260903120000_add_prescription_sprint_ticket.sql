-- services/gemini_service.py renders a Jira-style sprint ticket for every
-- ranked prescription -- the product's headline output (PRD 6.x, TRD pipeline
-- stage 7) -- but the original prescriptions table had nowhere to put it, so
-- finalize_report() dropped it on the floor and every persisted report showed
-- only the raw pattern-library recommended_action instead. The Gemini calls
-- were being paid for on every run and discarded milliseconds later.
--
-- Nullable, with no default: rows written before this migration genuinely have
-- no ticket text, and that's distinct from "rendered as an empty string." The
-- API/PDF/UI all fall back to recommended_action when it's null, which is
-- exactly what those older rows used to display anyway.
alter table public.prescriptions
  add column sprint_ticket text;
