-- Isolated test billing. These functions never issue invoices or entitlements.
grant usage on schema broker_internal to service_role;
create table if not exists private.broker_sandbox_intents(
 id uuid primary key default gen_random_uuid(),
 request_id uuid not null unique references private.membership_requests(request_id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 plan_id text not null check(plan_id in ('sector','multi','global')),
 amount_minor integer not null check(amount_minor>0),currency text not null check(currency='USD'),
 state text not null default 'prepared' check(state in ('prepared','creating','created','uncertain')),
 claim_id uuid,price_id text,product_id text,transaction_id text unique,
 created_at timestamptz not null default now()
);
create index if not exists broker_sandbox_intents_user_idx on private.broker_sandbox_intents(user_id);
create table if not exists private.broker_sandbox_receipts(
 event_id text primary key,transaction_id text not null unique,
 intent_id uuid not null unique references private.broker_sandbox_intents(id) on delete cascade,
 amount_minor integer not null,currency text not null check(currency='USD'),
 event_at timestamptz not null,projection_hash text not null,
 environment text not null default 'sandbox' check(environment='sandbox'),
 recorded_at timestamptz not null default now()
);
alter table private.broker_sandbox_intents enable row level security;
alter table private.broker_sandbox_receipts enable row level security;
revoke all on private.broker_sandbox_intents,private.broker_sandbox_receipts from public,anon,authenticated;

create or replace function broker_internal.prepare_sandbox_billing(p_request_id uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare uid uuid:=broker_internal.membership_user_check(); m private.membership_requests%rowtype;i private.broker_sandbox_intents%rowtype;
begin
 select * into m from private.membership_requests where request_id=p_request_id and user_id=uid;
 if not found then raise exception 'membership_not_found' using errcode='42501';end if;
 insert into private.broker_sandbox_intents(request_id,user_id,plan_id,amount_minor,currency)
 values(m.request_id,uid,m.plan_id,m.amount_minor,m.currency) on conflict(request_id) do nothing;
 select * into i from private.broker_sandbox_intents where request_id=m.request_id and user_id=uid;
 return jsonb_build_object('intent_id',i.id,'plan_id',i.plan_id,'amount_minor',i.amount_minor,'currency',i.currency,'state',i.state);
end $$;
revoke all on function broker_internal.prepare_sandbox_billing(uuid) from public,anon,authenticated;
grant execute on function broker_internal.prepare_sandbox_billing(uuid) to authenticated;
create or replace function public.gb_prepare_sandbox_billing(p_request_id uuid)
returns jsonb language sql security invoker set search_path='' as $$select broker_internal.prepare_sandbox_billing(p_request_id)$$;
revoke all on function public.gb_prepare_sandbox_billing(uuid) from public,anon;
grant execute on function public.gb_prepare_sandbox_billing(uuid) to authenticated;

create or replace function broker_internal.sandbox_service_check()
returns void language plpgsql stable security invoker set search_path='' as $$begin
 if (auth.jwt()->>'role') is distinct from 'service_role' then raise exception 'service_required' using errcode='42501';end if;
end $$;
revoke all on function broker_internal.sandbox_service_check() from public,anon,authenticated;

create or replace function broker_internal.claim_sandbox_billing(p_intent_id uuid,p_price_id text,p_product_id text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare i private.broker_sandbox_intents%rowtype;claim uuid;
begin
 perform broker_internal.sandbox_service_check();
 if p_price_id is null or p_price_id !~ '^pri_[a-z0-9]{26}$' or p_product_id is null or p_product_id !~ '^pro_[a-z0-9]{26}$' then raise exception 'invalid_catalog' using errcode='22023';end if;
 select * into i from private.broker_sandbox_intents where id=p_intent_id for update;
 if not found then raise exception 'intent_missing' using errcode='22023';end if;
 if i.state<>'prepared' then
  if i.price_id is distinct from p_price_id or i.product_id is distinct from p_product_id then raise exception 'catalog_changed' using errcode='22023';end if;
  return jsonb_build_object('claimed',false,'state',i.state,'transaction_id',i.transaction_id);
 end if;
 claim:=pg_catalog.gen_random_uuid();
 update private.broker_sandbox_intents set state='creating',claim_id=claim,price_id=p_price_id,product_id=p_product_id where id=i.id;
 return jsonb_build_object('claimed',true,'claim_id',claim,'state','creating');
end $$;
create or replace function broker_internal.finish_sandbox_billing(p_intent_id uuid,p_claim_id uuid,p_transaction_id text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare i private.broker_sandbox_intents%rowtype;
begin
 perform broker_internal.sandbox_service_check();
 select * into i from private.broker_sandbox_intents where id=p_intent_id for update;
 if not found or i.state<>'creating' or p_claim_id is null or i.claim_id is distinct from p_claim_id then raise exception 'claim_conflict' using errcode='22023';end if;
 if p_transaction_id is not null and p_transaction_id !~ '^txn_[a-z0-9]{26}$' then raise exception 'invalid_transaction' using errcode='22023';end if;
 update private.broker_sandbox_intents set state=case when p_transaction_id is null then 'uncertain' else 'created' end,transaction_id=p_transaction_id where id=i.id;
 return jsonb_build_object('stored',true);
end $$;
create or replace function broker_internal.record_sandbox_billing(p_receipt jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare i private.broker_sandbox_intents%rowtype;r private.broker_sandbox_receipts%rowtype;
begin
 perform broker_internal.sandbox_service_check();
 if p_receipt->>'environment' is distinct from 'sandbox' or p_receipt->>'event_type' is distinct from 'transaction.completed'
 or coalesce(p_receipt->>'event_id','') !~ '^evt_[a-z0-9]{26}$' or coalesce(p_receipt->>'projection_hash','') !~ '^[a-f0-9]{64}$' then raise exception 'invalid_receipt' using errcode='22023';end if;
 select * into i from private.broker_sandbox_intents where id=(p_receipt->>'intent_id')::uuid for update;
 if not found or i.state<>'created' or i.transaction_id is distinct from p_receipt->>'transaction_id'
 or i.price_id is distinct from p_receipt->>'price_id' or i.product_id is distinct from p_receipt->>'product_id'
 or i.amount_minor is distinct from (p_receipt->>'amount_minor')::integer or i.currency is distinct from p_receipt->>'currency'
 then raise exception 'receipt_context_mismatch' using errcode='22023';end if;
 select * into r from private.broker_sandbox_receipts where event_id=p_receipt->>'event_id';
 if found then
  if r.projection_hash is distinct from p_receipt->>'projection_hash' or r.intent_id<>i.id then raise exception 'event_conflict' using errcode='22023';end if;
  return jsonb_build_object('recorded',true,'duplicate',true,'production_access_changed',false);
 end if;
 if exists(select 1 from private.broker_sandbox_receipts where intent_id=i.id or transaction_id=i.transaction_id) then raise exception 'receipt_already_recorded' using errcode='22023';end if;
 insert into private.broker_sandbox_receipts(event_id,transaction_id,intent_id,amount_minor,currency,event_at,projection_hash)
 values(p_receipt->>'event_id',i.transaction_id,i.id,i.amount_minor,i.currency,(p_receipt->>'event_at')::timestamptz,p_receipt->>'projection_hash');
 return jsonb_build_object('recorded',true,'duplicate',false,'production_access_changed',false);
end $$;
revoke all on function broker_internal.claim_sandbox_billing(uuid,text,text),broker_internal.finish_sandbox_billing(uuid,uuid,text),broker_internal.record_sandbox_billing(jsonb) from public,anon,authenticated;
grant execute on function broker_internal.claim_sandbox_billing(uuid,text,text),broker_internal.finish_sandbox_billing(uuid,uuid,text),broker_internal.record_sandbox_billing(jsonb) to service_role;
create or replace function public.gb_claim_sandbox_billing(p_intent_id uuid,p_price_id text,p_product_id text)
returns jsonb language sql security invoker set search_path='' as $$select broker_internal.claim_sandbox_billing(p_intent_id,p_price_id,p_product_id)$$;
create or replace function public.gb_finish_sandbox_billing(p_intent_id uuid,p_claim_id uuid,p_transaction_id text)
returns jsonb language sql security invoker set search_path='' as $$select broker_internal.finish_sandbox_billing(p_intent_id,p_claim_id,p_transaction_id)$$;
create or replace function public.gb_record_sandbox_billing(p_receipt jsonb)
returns jsonb language sql security invoker set search_path='' as $$select broker_internal.record_sandbox_billing(p_receipt)$$;
revoke all on function public.gb_claim_sandbox_billing(uuid,text,text),public.gb_finish_sandbox_billing(uuid,uuid,text),public.gb_record_sandbox_billing(jsonb) from public,anon,authenticated;
grant execute on function public.gb_claim_sandbox_billing(uuid,text,text),public.gb_finish_sandbox_billing(uuid,uuid,text),public.gb_record_sandbox_billing(jsonb) to service_role;

create or replace function broker_internal.sandbox_billing_workspace()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare uid uuid:=broker_internal.membership_user_check(); rows jsonb;
begin
 select coalesce(jsonb_agg(jsonb_build_object('request_id',i.request_id,'plan_id',i.plan_id,'state',i.state,'receipt_status',case when r.event_id is null then 'awaiting_signed_receipt' else 'sandbox_completed' end,'amount_minor',i.amount_minor,'currency',i.currency)),'[]'::jsonb)
 into rows from private.broker_sandbox_intents i left join private.broker_sandbox_receipts r on r.intent_id=i.id where i.user_id=uid;
 return jsonb_build_object('environment','sandbox','production_access_changed',false,'records',rows);
end $$;
revoke all on function broker_internal.sandbox_billing_workspace() from public,anon;
grant execute on function broker_internal.sandbox_billing_workspace() to authenticated;
create or replace function public.gb_sandbox_billing_workspace()
returns jsonb language sql stable security invoker set search_path='' as $$select broker_internal.sandbox_billing_workspace()$$;
revoke all on function public.gb_sandbox_billing_workspace() from public,anon;
grant execute on function public.gb_sandbox_billing_workspace() to authenticated;
