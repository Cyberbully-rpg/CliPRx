-- CliPRx Phase 2 core schema (TRD v1.0 section 4)
-- profiles, uploads, reports, prescriptions -- with Row Level Security so a user
-- can only ever see their own rows. FastAPI uses the service role key to bypass
-- RLS where required (TRD section 4 intro).

-- ============================================================================
-- profiles (TRD 4.1)
-- ============================================================================
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles_select_own"
  on public.profiles for select
  using (auth.uid() = id);

create policy "profiles_update_own"
  on public.profiles for update
  using (auth.uid() = id);

-- Supabase Auth populates auth.users on signup; nothing populates public.profiles
-- automatically, so mirror new signups into it via trigger.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================================
-- uploads (TRD 4.2)
-- ============================================================================
create table public.uploads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  cloud_provider text not null check (cloud_provider in ('aws', 'azure', 'gcp')),
  file_path text not null,
  file_size_bytes bigint not null,
  service_count integer not null,
  parse_warnings jsonb not null default '[]',
  created_at timestamptz not null default now()
);

create index uploads_user_id_idx on public.uploads(user_id);

alter table public.uploads enable row level security;

create policy "uploads_select_own"
  on public.uploads for select
  using (auth.uid() = user_id);

create policy "uploads_insert_own"
  on public.uploads for insert
  with check (auth.uid() = user_id);

-- ============================================================================
-- reports (TRD 4.3)
-- ============================================================================
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  upload_id uuid not null references public.uploads(id) on delete cascade,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'complete', 'failed')),
  total_savings_min numeric(10, 2),
  total_savings_max numeric(10, 2),
  prescription_count integer,
  conflict_count integer,
  pdf_path text,
  expires_at timestamptz not null default (now() + interval '30 days'),
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index reports_user_id_idx on public.reports(user_id);
create index reports_upload_id_idx on public.reports(upload_id);
create index reports_expires_at_idx on public.reports(expires_at);

alter table public.reports enable row level security;

create policy "reports_select_own"
  on public.reports for select
  using (auth.uid() = user_id and deleted_at is null);

create policy "reports_insert_own"
  on public.reports for insert
  with check (auth.uid() = user_id);

create policy "reports_update_own"
  on public.reports for update
  using (auth.uid() = user_id);

-- ============================================================================
-- prescriptions (TRD 4.4)
-- ============================================================================
create table public.prescriptions (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references public.reports(id) on delete cascade,
  service_name text not null,
  anomaly_score numeric(5, 4) not null,
  pattern_id text not null,
  recommended_action text not null,
  savings_min numeric(10, 2) not null,
  savings_max numeric(10, 2) not null,
  engineering_hours numeric(6, 2) not null,
  risk_level text not null check (risk_level in ('Low', 'Medium', 'High')),
  failure_cost_estimate numeric(10, 2),
  roi_score numeric(10, 4) not null,
  rank_position integer not null,
  is_conflicted boolean not null default false,
  conflict_reason text,
  tier smallint not null check (tier in (1, 2, 3))
);

create index prescriptions_report_id_idx on public.prescriptions(report_id);

alter table public.prescriptions enable row level security;

-- prescriptions has no user_id column of its own -- ownership is via its parent
-- report, so the policy joins through reports.
create policy "prescriptions_select_own"
  on public.prescriptions for select
  using (
    exists (
      select 1 from public.reports
      where reports.id = prescriptions.report_id
        and reports.user_id = auth.uid()
    )
  );

create policy "prescriptions_insert_own"
  on public.prescriptions for insert
  with check (
    exists (
      select 1 from public.reports
      where reports.id = prescriptions.report_id
        and reports.user_id = auth.uid()
    )
  );

-- ============================================================================
-- Retention (TRD 8.3): nightly hard-delete of expired reports.
-- Requires the pg_cron extension. If this section fails, enable pg_cron via
-- the Supabase dashboard (Database > Extensions) and re-run just this part.
-- ============================================================================
create extension if not exists pg_cron with schema extensions;

select
  cron.schedule(
    'cliprx-report-retention',
    '0 3 * * *', -- 03:00 UTC nightly
    $$ delete from public.reports where expires_at < now(); $$
  );
