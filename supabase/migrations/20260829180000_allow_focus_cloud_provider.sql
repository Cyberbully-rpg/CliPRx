-- The uploads.cloud_provider check constraint predates the FOCUS parser
-- (backend/parsers/focus_parser.py) and the "focus" upload-UI option -- both
-- shipped after this table's original constraint was written, so uploads
-- with cloud_provider='focus' were rejected at the database layer even
-- though the application fully supports it.
alter table public.uploads
  drop constraint uploads_cloud_provider_check;

alter table public.uploads
  add constraint uploads_cloud_provider_check
  check (cloud_provider in ('aws', 'azure', 'gcp', 'focus'));
