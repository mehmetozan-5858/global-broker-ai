-- Global Broker contact unlock accounting.
-- The browser never updates credits directly. This SECURITY DEFINER RPC only debits the
-- authenticated user's own entitlement and records idempotent unlocks. It does not return
-- contact data; contact disclosure remains a server API responsibility.

create table if not exists private.contact_credit_unlocks (
  user_id uuid not null references auth.users(id) on delete cascade,
  opportunity_id text not null,
  unlocked_at timestamptz not null default now(),
  primary key (user_id, opportunity_id)
);

alter table private.contact_credit_unlocks enable row level security;
revoke all on private.contact_credit_unlocks from public, anon, authenticated;
grant select, insert, update, delete on private.contact_credit_unlocks to service_role;

create or replace function public.consume_contact_credit(p_opportunity_id text)
returns jsonb
language plpgsql
security definer
set search_path=public,private,auth
as $$
declare
  uid uuid := auth.uid();
  ent public.customer_entitlements%rowtype;
  already boolean;
  remaining integer;
begin
  if uid is null then
    raise exception 'authentication_required';
  end if;
  if p_opportunity_id is null or length(trim(p_opportunity_id)) < 8 or length(p_opportunity_id) > 200 then
    raise exception 'invalid_opportunity_id';
  end if;

  select * into ent
  from public.customer_entitlements
  where user_id=uid and active=true
  for update;

  if not found then
    raise exception 'active_plan_required';
  end if;

  select exists(
    select 1 from private.contact_credit_unlocks
    where user_id=uid and opportunity_id=p_opportunity_id
  ) into already;

  if already then
    return jsonb_build_object(
      'ok',true,
      'already_unlocked',true,
      'credits_remaining',ent.contact_credits_remaining
    );
  end if;

  if ent.contact_credits_remaining is not null and ent.contact_credits_remaining <= 0 then
    raise exception 'contact_credit_required';
  end if;

  insert into private.contact_credit_unlocks(user_id,opportunity_id)
  values(uid,p_opportunity_id);

  if ent.contact_credits_remaining is not null then
    update public.customer_entitlements
    set contact_credits_remaining=contact_credits_remaining-1, updated_at=now()
    where user_id=uid
    returning contact_credits_remaining into remaining;
  else
    remaining := null;
  end if;

  insert into private.audit_log(opportunity_id,actor_id,event_type,details)
  values(null,uid::text,'contact_credit_consumed',jsonb_build_object(
    'opportunity_id',p_opportunity_id,
    'plan_id',ent.plan_id,
    'already_unlocked',false
  ));

  return jsonb_build_object(
    'ok',true,
    'already_unlocked',false,
    'credits_remaining',remaining
  );
end;
$$;

revoke all on function public.consume_contact_credit(text) from public, anon;
grant execute on function public.consume_contact_credit(text) to authenticated;
