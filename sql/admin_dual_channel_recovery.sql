-- Applied to Supabase production project on 2026-10-10.
-- Admin privilege stays fail-closed until email + phone MFA + SMS provider are verified.

create table if not exists public.admin_recovery_enrollment (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email_verified_at timestamptz,
  phone_e164 text,
  phone_verified_at timestamptz,
  phone_factor_id text,
  sms_provider_verified boolean not null default false,
  enabled boolean not null default false,
  updated_at timestamptz not null default now()
);

alter table public.admin_recovery_enrollment enable row level security;
revoke all on public.admin_recovery_enrollment from anon;
grant select on public.admin_recovery_enrollment to authenticated;

drop policy if exists admin_recovery_select_own on public.admin_recovery_enrollment;
create policy admin_recovery_select_own
on public.admin_recovery_enrollment
for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists admin_role_requires_aal2 on public.user_roles;
create policy admin_role_requires_aal2
on public.user_roles
as restrictive
for select
to authenticated
using (role <> 'admin' or (select auth.jwt()->>'aal') = 'aal2');

create or replace function private.guard_admin_role_recovery()
returns trigger
language plpgsql
security definer
set search_path = public, private
as $$
begin
  if new.role = 'admin' then
    if not exists (
      select 1 from public.admin_recovery_enrollment e
      where e.user_id = new.user_id
        and e.email_verified_at is not null
        and e.phone_verified_at is not null
        and e.sms_provider_verified is true
        and e.enabled is true
    ) then
      raise exception 'admin_dual_channel_recovery_not_ready';
    end if;
  end if;
  return new;
end;
$$;

revoke all on function private.guard_admin_role_recovery() from public;
revoke all on function private.guard_admin_role_recovery() from anon;
revoke all on function private.guard_admin_role_recovery() from authenticated;

drop trigger if exists user_roles_admin_recovery_guard on public.user_roles;
create trigger user_roles_admin_recovery_guard
before insert or update of role on public.user_roles
for each row execute function private.guard_admin_role_recovery();
