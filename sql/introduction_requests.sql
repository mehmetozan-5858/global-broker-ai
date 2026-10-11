-- Global Broker controlled introduction workflow.
-- Credits buy a verified introduction request, never an immediate raw contact dump.

create table if not exists private.introduction_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  opportunity_id text not null,
  status text not null default 'requested' check (status in (
    'requested','verifying','buyer_consent_pending','approved','introduced',
    'declined','expired','refunded'
  )),
  credit_charged boolean not null default false,
  credit_refunded boolean not null default false,
  reason text,
  requested_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  approved_at timestamptz,
  introduced_at timestamptz,
  refunded_at timestamptz,
  unique(user_id, opportunity_id)
);

create index if not exists introduction_requests_user_status_idx
  on private.introduction_requests(user_id,status,requested_at desc);
create index if not exists introduction_requests_status_idx
  on private.introduction_requests(status,requested_at);

alter table private.introduction_requests enable row level security;
revoke all on private.introduction_requests from public, anon, authenticated;
grant select, insert, update, delete on private.introduction_requests to service_role;

create or replace function public.request_introduction(p_opportunity_id text)
returns jsonb
language plpgsql
security definer
set search_path=public,private,auth
as $$
declare
  uid uuid := auth.uid();
  ent public.customer_entitlements%rowtype;
  pref public.customer_preferences%rowtype;
  opp jsonb;
  sector_id text;
  country_code text;
  req private.introduction_requests%rowtype;
  remaining integer;
begin
  if uid is null then raise exception 'authentication_required'; end if;
  if p_opportunity_id is null or length(trim(p_opportunity_id)) < 8 or length(p_opportunity_id) > 200 then
    raise exception 'invalid_opportunity_id';
  end if;

  select * into ent from public.customer_entitlements
  where user_id=uid and active=true for update;
  if not found then raise exception 'active_plan_required'; end if;

  select * into pref from public.customer_preferences where user_id=uid;
  if not found then
    pref.user_id := uid;
    pref.selected_sectors := '{}'::text[];
    pref.selected_countries := '{}'::text[];
  end if;

  select opportunity into opp from private.opportunities where id=p_opportunity_id;
  if opp is null then raise exception 'opportunity_not_found'; end if;

  sector_id := coalesce(opp->>'sector_id',opp->>'sector','');
  country_code := upper(coalesce(opp->>'country_code',opp->>'buyer_country_code',''));

  if not ent.all_sectors and not (sector_id = any(coalesce(pref.selected_sectors,'{}'::text[]))) then
    raise exception 'sector_not_in_plan';
  end if;
  if coalesce(array_length(pref.selected_countries,1),0) > 0
     and (country_code = '' or not (country_code = any(pref.selected_countries))) then
    raise exception 'country_not_selected';
  end if;

  select * into req from private.introduction_requests
  where user_id=uid and opportunity_id=p_opportunity_id
  for update;

  if found and req.status not in ('declined','expired','refunded') then
    return jsonb_build_object(
      'ok',true,
      'already_requested',true,
      'request_id',req.id,
      'status',req.status,
      'credits_remaining',ent.contact_credits_remaining
    );
  end if;

  if ent.contact_credits_remaining is not null and ent.contact_credits_remaining <= 0 then
    raise exception 'introduction_credit_required';
  end if;

  if ent.contact_credits_remaining is not null then
    update public.customer_entitlements
      set contact_credits_remaining=contact_credits_remaining-1, updated_at=now()
      where user_id=uid
      returning contact_credits_remaining into remaining;
  else
    remaining := null;
  end if;

  if found then
    update private.introduction_requests
      set status='requested', credit_charged=true, credit_refunded=false,
          reason=null, requested_at=now(), updated_at=now(), approved_at=null,
          introduced_at=null, refunded_at=null
      where id=req.id
      returning * into req;
  else
    insert into private.introduction_requests(user_id,opportunity_id,status,credit_charged)
      values(uid,p_opportunity_id,'requested',true)
      returning * into req;
  end if;

  insert into private.audit_log(opportunity_id,actor_id,event_type,details)
  values(p_opportunity_id,uid::text,'introduction_requested',jsonb_build_object(
    'request_id',req.id,'plan_id',ent.plan_id,'credit_charged',true
  ));

  return jsonb_build_object(
    'ok',true,
    'already_requested',false,
    'request_id',req.id,
    'status',req.status,
    'credits_remaining',remaining
  );
end;
$$;

create or replace function public.my_introduction_requests()
returns jsonb
language sql
stable
security definer
set search_path=public,private,auth
as $$
  select coalesce(jsonb_agg(jsonb_build_object(
    'request_id',r.id,
    'opportunity_id',r.opportunity_id,
    'status',r.status,
    'requested_at',r.requested_at,
    'updated_at',r.updated_at,
    'approved_at',r.approved_at,
    'introduced_at',r.introduced_at,
    'refunded_at',r.refunded_at,
    'credit_refunded',r.credit_refunded
  ) order by r.requested_at desc),'[]'::jsonb)
  from private.introduction_requests r
  where r.user_id=(select auth.uid());
$$;

create or replace function public.set_introduction_status(
  p_request_id uuid,
  p_status text,
  p_reason text default null
)
returns jsonb
language plpgsql
security definer
set search_path=public,private,auth
as $$
declare
  req private.introduction_requests%rowtype;
  jwt_role text := coalesce(current_setting('request.jwt.claim.role',true),'');
  should_refund boolean := false;
begin
  if jwt_role <> 'service_role' then raise exception 'service_role_required'; end if;
  if p_status not in ('requested','verifying','buyer_consent_pending','approved','introduced','declined','expired','refunded') then
    raise exception 'invalid_introduction_status';
  end if;

  select * into req from private.introduction_requests where id=p_request_id for update;
  if not found then raise exception 'introduction_request_not_found'; end if;

  should_refund := p_status in ('declined','expired','refunded')
                   and req.credit_charged and not req.credit_refunded;

  if should_refund then
    update public.customer_entitlements
      set contact_credits_remaining = case
        when contact_credits_remaining is null then null
        else contact_credits_remaining + 1
      end,
      updated_at=now()
      where user_id=req.user_id;
  end if;

  update private.introduction_requests
    set status=p_status,
        reason=p_reason,
        updated_at=now(),
        approved_at=case when p_status='approved' then now() else approved_at end,
        introduced_at=case when p_status='introduced' then now() else introduced_at end,
        credit_refunded=case when should_refund then true else credit_refunded end,
        refunded_at=case when should_refund then now() else refunded_at end
    where id=p_request_id
    returning * into req;

  insert into private.audit_log(opportunity_id,actor_id,event_type,details)
  values(req.opportunity_id,'service_role','introduction_status_changed',jsonb_build_object(
    'request_id',req.id,'status',req.status,'reason',p_reason,'credit_refunded',should_refund
  ));

  return jsonb_build_object('ok',true,'request_id',req.id,'status',req.status,'credit_refunded',req.credit_refunded);
end;
$$;

revoke all on function public.request_introduction(text) from public, anon;
grant execute on function public.request_introduction(text) to authenticated;
revoke all on function public.my_introduction_requests() from public, anon;
grant execute on function public.my_introduction_requests() to authenticated;
revoke all on function public.set_introduction_status(uuid,text,text) from public, anon, authenticated;
grant execute on function public.set_introduction_status(uuid,text,text) to service_role;

-- Deprecate direct contact unlocking for customer sessions.
revoke execute on function public.consume_contact_credit(text) from authenticated;
revoke execute on function public.unlock_opportunity_contact(text) from authenticated;
