-- CliPRx Phase 2 storage buckets (TRD 8.3)
-- cliprx-uploads: raw CSV files. cliprx-reports: PDF exports (not generated yet,
-- bucket created now so it's ready when PDF export is built).
-- Storage policy per TRD 8.3: "authenticated users read/write only their own
-- files" -- enforced by requiring the object path's first folder segment to
-- equal the requesting user's auth.uid().

insert into storage.buckets (id, name, public)
values
  ('cliprx-uploads', 'cliprx-uploads', false),
  ('cliprx-reports', 'cliprx-reports', false)
on conflict (id) do nothing;

create policy "cliprx_uploads_select_own"
  on storage.objects for select
  using (
    bucket_id = 'cliprx-uploads'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "cliprx_uploads_insert_own"
  on storage.objects for insert
  with check (
    bucket_id = 'cliprx-uploads'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "cliprx_reports_select_own"
  on storage.objects for select
  using (
    bucket_id = 'cliprx-reports'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "cliprx_reports_insert_own"
  on storage.objects for insert
  with check (
    bucket_id = 'cliprx-reports'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
