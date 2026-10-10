-- Global Broker Supabase hardening applied to the live project on 2026-10-10.
-- Idempotent reconciliation script: keeps RLS efficient, enforces admin AAL2 role reads,
-- reduces unnecessary SECURITY DEFINER surface, and adds the contact-unlock FK index.

-- RLS performance: evaluate auth.uid() once per statement rather than per row.
drop policy if exists profile_select_own on public.customer_profiles;
create policy profile_select_own on public.customer_profiles
for select to authenticated using ((select auth.uid()) = user_id);

drop policy if exists profile_insert_own on public.customer_profiles;
create policy profile_insert_own on public.customer_profiles
for insert to authenticated with check ((select auth.uid()) = user_id);

drop policy if exists profile_update_own on public.customer_profiles;
create policy profile_update_own on public.customer_profiles
for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists access_select_own on public.private_opportunity_access;
create policy access_select_own on public.private_opportunity_access
for select to authenticated
using (((select auth.uid()) = user_id) and (expires_at is null or expires_at > now()));

drop policy if exists customer_entitlements_select_own on public.customer_entitlements;
create policy customer_entitlements_select_own on public.customer_entitlements
for select to authenticated using ((select auth.uid()) = user_id);

drop policy if exists customer_preferences_select_own on public.customer_preferences;
create policy customer_preferences_select_own on public.customer_preferences
for select to authenticated using ((select auth.uid()) = user_id);

drop policy if exists customer_preferences_insert_own on public.customer_preferences;
create policy customer_preferences_insert_own on public.customer_preferences
for insert to authenticated with check ((select auth.uid()) = user_id);

drop policy if exists customer_preferences_update_own on public.customer_preferences;
create policy customer_preferences_update_own on public.customer_preferences
for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

-- Important: PostgreSQL permissive policies are ORed. Keep the ownership and AAL2
-- requirements in one policy so another SELECT policy cannot bypass MFA for admins.
drop policy if exists role_select_own on public.user_roles;
drop policy if exists admin_role_requires_aal2 on public.user_roles;
drop policy if exists role_select_own_aal2 on public.user_roles;
create policy role_select_own_aal2 on public.user_roles
for select to authenticated
using (
  (select auth.uid()) = user_id
  and (
    role <> 'admin'
    or ((select auth.jwt()) ->> 'aal') = 'aal2'
  )
);

-- The trigger function is not a public RPC.
revoke all on function public.gb_new_user_defaults() from public, anon, authenticated;

-- These functions can rely on table RLS and therefore do not need definer privileges.
create or replace function public.my_broker_access()
returns jsonb
language sql
stable
security invoker
set search_path to 'public','private','auth'
as $function$
  select jsonb_build_object(
    'entitlement',to_jsonb(e),
    'preferences',to_jsonb(p)
  )
  from public.customer_entitlements e
  left join public.customer_preferences p on p.user_id=e.user_id
  where e.user_id=(select auth.uid());
$function$;

create or replace function public.set_customer_preferences(
  p_sectors text[], p_countries text[] default '{}'::text[]
)
returns jsonb
language plpgsql
security invoker
set search_path to 'public','private','auth'
as $function$
declare
  uid uuid := (select auth.uid());
  ent public.customer_entitlements%rowtype;
  sectors text[] := coalesce(p_sectors,'{}'::text[]);
  countries text[] := coalesce(p_countries,'{}'::text[]);
  valid_sectors constant text[] := array['furniture','machinery','textile','automotive','packaging','construction','food','chemicals','electronics','medical'];
  x text;
begin
  if uid is null then raise exception 'authentication_required'; end if;
  select * into ent from public.customer_entitlements where user_id=uid and active=true;
  if not found then raise exception 'active_plan_required'; end if;
  if not ent.all_sectors and coalesce(array_length(sectors,1),0) > coalesce(ent.sector_limit,0) then
    raise exception 'sector_limit_exceeded';
  end if;
  if ent.country_limit is not null and coalesce(array_length(countries,1),0) > ent.country_limit then
    raise exception 'country_limit_exceeded';
  end if;
  foreach x in array sectors loop
    if not (x = any(valid_sectors)) then raise exception 'invalid_sector'; end if;
  end loop;
  foreach x in array countries loop
    if x !~ '^[A-Z]{2}$' then raise exception 'invalid_country_code'; end if;
  end loop;
  insert into public.customer_preferences(user_id,selected_sectors,selected_countries,updated_at)
  values(uid,sectors,countries,now())
  on conflict(user_id) do update
  set selected_sectors=excluded.selected_sectors,
      selected_countries=excluded.selected_countries,
      updated_at=now();
  return jsonb_build_object('ok',true,'sectors',sectors,'countries',countries);
end;$function$;

revoke all on function public.my_broker_access() from public, anon;
grant execute on function public.my_broker_access() to authenticated;
revoke all on function public.set_customer_preferences(text[],text[]) from public, anon;
grant execute on function public.set_customer_preferences(text[],text[]) to authenticated;

-- Deliberate privileged boundary: this RPC must atomically read private opportunities,
-- decrement server-owned credits and write audit/contact-unlock records. It remains
-- SECURITY DEFINER but is authenticated-only and performs auth.uid(), active-plan,
-- sector, country and credit checks before any private write.
revoke all on function public.unlock_opportunity_contact(text) from public, anon;
grant execute on function public.unlock_opportunity_contact(text) to authenticated;

create index if not exists contact_unlocks_opportunity_id_idx
on private.contact_unlocks (opportunity_id);
