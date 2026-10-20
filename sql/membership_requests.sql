-- Membership interest only: no checkout, invoice issue or entitlement mutation.
create table if not exists private.membership_requests (
 request_id uuid primary key,
 user_id uuid not null references auth.users(id) on delete cascade,
 plan_id text not null check(plan_id in ('sector','multi','global')),
 amount_minor integer not null check(amount_minor>0),
 currency text not null check(currency='USD'),
 policy_version text not null,
 terms_version text not null,
 requested_at timestamptz not null default now(),
 status text not null default 'awaiting_provider' check(status='awaiting_provider'),
 invoice_status text not null default 'not_issued' check(invoice_status='not_issued'),
 unique(user_id,plan_id)
);
alter table private.membership_requests enable row level security;
revoke all on private.membership_requests from public,anon,authenticated;

create or replace function broker_internal.membership_user_check()
returns uuid language plpgsql stable security definer set search_path='' as $$
declare uid uuid:=auth.uid();
begin
 if uid is null or not exists(select 1 from auth.users where id=uid and email_confirmed_at is not null) then
  raise exception 'verified_account_required' using errcode='42501';
 end if;
 return uid;
end $$;
revoke all on function broker_internal.membership_user_check() from public,anon,authenticated;

create or replace function broker_internal.membership_workspace()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare uid uuid:=broker_internal.membership_user_check(); rows jsonb; current_plan text;
begin
 select coalesce(jsonb_agg(to_jsonb(r)-'user_id'),'[]'::jsonb) into rows
 from(select * from private.membership_requests where user_id=uid order by requested_at desc limit 10)r;
 select plan_id into current_plan from public.customer_entitlements where user_id=uid and active=true;
 return jsonb_build_object('checkout_enabled',false,'current_plan',coalesce(current_plan,'free'),'requests',rows,
 'catalog',jsonb_build_array(
 jsonb_build_object('id','sector','name','Sector Access','amount_minor',8900,'currency','USD'),
 jsonb_build_object('id','multi','name','Multi-Sector','amount_minor',17900,'currency','USD'),
 jsonb_build_object('id','global','name','Global Access','amount_minor',34900,'currency','USD')));
end $$;
revoke all on function broker_internal.membership_workspace() from public,anon,authenticated;
grant execute on function broker_internal.membership_workspace() to authenticated;

create or replace function broker_internal.request_membership(p_request_id uuid,p_plan_id text,p_terms_accepted boolean)
returns jsonb language plpgsql security definer set search_path='' as $$
declare uid uuid:=broker_internal.membership_user_check(); stored private.membership_requests%rowtype; price integer;
begin
 if p_request_id is null or p_plan_id is null or p_plan_id not in ('sector','multi','global') or p_terms_accepted is distinct from true then
  raise exception 'invalid_membership_request' using errcode='22023';
 end if;
 -- Serialize this owner's requests; other owners cannot claim or inspect an ID.
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(uid::text,781));
 select * into stored from private.membership_requests where request_id=p_request_id;
 if found then
  if stored.user_id<>uid or stored.plan_id<>p_plan_id then raise exception 'request_conflict' using errcode='22023'; end if;
  return jsonb_build_object('request_id',stored.request_id,'status',stored.status,'duplicate',true);
 end if;
 select * into stored from private.membership_requests where user_id=uid and plan_id=p_plan_id;
 if found then return jsonb_build_object('request_id',stored.request_id,'status',stored.status,'duplicate',true);end if;
 price:=case p_plan_id when 'sector' then 8900 when 'multi' then 17900 when 'global' then 34900 end;
 insert into private.membership_requests(request_id,user_id,plan_id,amount_minor,currency,policy_version,terms_version)
 values(p_request_id,uid,p_plan_id,price,'USD','2026-10-10-v2','2026-10-20')
 on conflict(request_id) do nothing;
 select * into stored from private.membership_requests where request_id=p_request_id;
 if stored.user_id<>uid or stored.plan_id<>p_plan_id then raise exception 'request_conflict' using errcode='22023';end if;
 return jsonb_build_object('request_id',stored.request_id,'status',stored.status,'duplicate',false);
end $$;
revoke all on function broker_internal.request_membership(uuid,text,boolean) from public,anon,authenticated;
grant execute on function broker_internal.request_membership(uuid,text,boolean) to authenticated;

create or replace function public.gb_membership_workspace()
returns jsonb language sql stable security invoker set search_path='' as $$select broker_internal.membership_workspace()$$;
create or replace function public.gb_request_membership(p_request_id uuid,p_plan_id text,p_terms_accepted boolean)
returns jsonb language sql security invoker set search_path='' as $$select broker_internal.request_membership(p_request_id,p_plan_id,p_terms_accepted)$$;
revoke all on function public.gb_membership_workspace() from public,anon;
revoke all on function public.gb_request_membership(uuid,text,boolean) from public,anon;
grant execute on function public.gb_membership_workspace() to authenticated;
grant execute on function public.gb_request_membership(uuid,text,boolean) to authenticated;
