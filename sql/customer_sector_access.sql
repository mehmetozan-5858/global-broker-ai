-- Global Broker customer plan, sector and contact-credit access model.
-- Billing entitlements are server-managed. Customers can only read their own entitlement
-- and change preferences through a validated RPC.

create table if not exists public.customer_entitlements (
  user_id uuid primary key references auth.users(id) on delete cascade,
  plan_id text not null default 'free' check (plan_id in ('free','sector','multi','global','enterprise')),
  sector_limit integer check (sector_limit is null or sector_limit >= 0),
  country_limit integer check (country_limit is null or country_limit >= 0),
  contact_credits_monthly integer check (contact_credits_monthly is null or contact_credits_monthly >= 0),
  contact_credits_remaining integer check (contact_credits_remaining is null or contact_credits_remaining >= 0),
  all_sectors boolean not null default false,
  commission_multiplier numeric(6,4),
  active boolean not null default true,
  current_period_start timestamptz not null default now(),
  current_period_end timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists public.customer_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  selected_sectors text[] not null default '{}'::text[],
  selected_countries text[] not null default '{}'::text[],
  updated_at timestamptz not null default now()
);

create table if not exists private.contact_unlocks (
  user_id uuid not null references auth.users(id) on delete cascade,
  opportunity_id text not null references private.opportunities(id) on delete cascade,
  unlocked_at timestamptz not null default now(),
  primary key (user_id, opportunity_id)
);

alter table public.customer_entitlements enable row level security;
alter table public.customer_preferences enable row level security;
alter table private.contact_unlocks enable row level security;

drop policy if exists customer_entitlements_select_own on public.customer_entitlements;
create policy customer_entitlements_select_own on public.customer_entitlements
for select to authenticated using (auth.uid() = user_id);

drop policy if exists customer_preferences_select_own on public.customer_preferences;
create policy customer_preferences_select_own on public.customer_preferences
for select to authenticated using (auth.uid() = user_id);

revoke insert, update, delete on public.customer_entitlements from anon, authenticated;
revoke insert, update, delete on public.customer_preferences from anon, authenticated;
revoke all on private.contact_unlocks from public, anon, authenticated;
grant select on public.customer_entitlements, public.customer_preferences to authenticated;
grant select, insert, update, delete on public.customer_entitlements, public.customer_preferences to service_role;
grant select, insert, update, delete on private.contact_unlocks to service_role;

create or replace function public.gb_default_entitlement(p_user uuid)
returns void language plpgsql security definer set search_path=public,private,auth as $$
begin
  insert into public.customer_entitlements(
    user_id,plan_id,sector_limit,country_limit,contact_credits_monthly,
    contact_credits_remaining,all_sectors,commission_multiplier,active
  ) values (p_user,'free',1,3,0,0,false,1.0000,true)
  on conflict (user_id) do nothing;
  insert into public.customer_preferences(user_id) values (p_user)
  on conflict (user_id) do nothing;
end;$$;
revoke all on function public.gb_default_entitlement(uuid) from public, anon, authenticated;
grant execute on function public.gb_default_entitlement(uuid) to service_role;

create or replace function public.gb_new_user_defaults()
returns trigger language plpgsql security definer set search_path=public,private,auth as $$
begin
  perform public.gb_default_entitlement(new.id);
  return new;
end;$$;

drop trigger if exists gb_auth_user_defaults on auth.users;
create trigger gb_auth_user_defaults after insert on auth.users
for each row execute function public.gb_new_user_defaults();

-- Backfill existing accounts safely as Free unless a server-side billing process upgrades them.
do $$ declare r record; begin
  for r in select id from auth.users loop
    perform public.gb_default_entitlement(r.id);
  end loop;
end $$;

create or replace function public.set_customer_preferences(
  p_sectors text[], p_countries text[] default '{}'::text[]
) returns jsonb language plpgsql security definer set search_path=public,private,auth as $$
declare
  uid uuid := auth.uid();
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
  on conflict(user_id) do update set selected_sectors=excluded.selected_sectors,selected_countries=excluded.selected_countries,updated_at=now();

  return jsonb_build_object('ok',true,'sectors',sectors,'countries',countries);
end;$$;
revoke all on function public.set_customer_preferences(text[],text[]) from public, anon;
grant execute on function public.set_customer_preferences(text[],text[]) to authenticated;

create or replace function public.unlock_opportunity_contact(p_opportunity_id text)
returns jsonb language plpgsql security definer set search_path=public,private,auth as $$
declare
  uid uuid := auth.uid();
  ent public.customer_entitlements%rowtype;
  pref public.customer_preferences%rowtype;
  opp jsonb;
  sector_id text;
  country_code text;
  already boolean;
begin
  if uid is null then raise exception 'authentication_required'; end if;
  select * into ent from public.customer_entitlements where user_id=uid and active=true for update;
  if not found then raise exception 'active_plan_required'; end if;
  select * into pref from public.customer_preferences where user_id=uid;
  select opportunity into opp from private.opportunities where id=p_opportunity_id;
  if opp is null then raise exception 'opportunity_not_found'; end if;

  sector_id := coalesce(opp->>'sector_id',opp->>'sector','');
  country_code := upper(coalesce(opp->>'country_code',opp->>'buyer_country_code',''));
  if not ent.all_sectors and not (sector_id = any(coalesce(pref.selected_sectors,'{}'::text[]))) then
    raise exception 'sector_not_in_plan';
  end if;
  if coalesce(array_length(pref.selected_countries,1),0) > 0 and country_code <> ''
     and not (country_code = any(pref.selected_countries)) then
    raise exception 'country_not_selected';
  end if;

  select exists(select 1 from private.contact_unlocks where user_id=uid and opportunity_id=p_opportunity_id) into already;
  if already then
    return jsonb_build_object('ok',true,'already_unlocked',true,'credits_remaining',ent.contact_credits_remaining);
  end if;
  if ent.contact_credits_remaining is not null and ent.contact_credits_remaining <= 0 then
    raise exception 'contact_credit_required';
  end if;

  insert into private.contact_unlocks(user_id,opportunity_id) values(uid,p_opportunity_id);
  if ent.contact_credits_remaining is not null then
    update public.customer_entitlements set contact_credits_remaining=contact_credits_remaining-1,updated_at=now() where user_id=uid;
  end if;
  insert into private.audit_log(opportunity_id,actor_id,event_type,details)
  values(p_opportunity_id,uid::text,'contact_unlocked',jsonb_build_object('plan_id',ent.plan_id));
  return jsonb_build_object('ok',true,'already_unlocked',false,'credits_remaining',case when ent.contact_credits_remaining is null then null else ent.contact_credits_remaining-1 end);
end;$$;
revoke all on function public.unlock_opportunity_contact(text) from public, anon;
grant execute on function public.unlock_opportunity_contact(text) to authenticated;

create or replace function public.my_broker_access()
returns jsonb language sql stable security definer set search_path=public,private,auth as $$
  select jsonb_build_object(
    'entitlement',to_jsonb(e),
    'preferences',to_jsonb(p)
  )
  from public.customer_entitlements e
  left join public.customer_preferences p on p.user_id=e.user_id
  where e.user_id=auth.uid();
$$;
revoke all on function public.my_broker_access() from public, anon;
grant execute on function public.my_broker_access() to authenticated;
