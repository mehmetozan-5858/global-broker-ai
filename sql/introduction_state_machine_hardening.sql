-- Harden controlled introduction state transitions and centralize credit refunds.

create or replace function private.gb_apply_introduction_transition(
  p_request_id uuid,
  p_status text,
  p_reason text default null,
  p_actor text default 'service_role'
)
returns jsonb
language plpgsql
security definer
set search_path=public,private,auth
as $$
declare
  req private.introduction_requests%rowtype;
  old_status text;
  allowed boolean := false;
  should_refund boolean := false;
begin
  if p_status not in ('requested','verifying','buyer_consent_pending','approved','introduced','declined','expired','refunded') then
    raise exception 'invalid_introduction_status';
  end if;

  select * into req from private.introduction_requests where id=p_request_id for update;
  if not found then raise exception 'introduction_request_not_found'; end if;
  old_status := req.status;

  allowed := old_status = p_status
    or (old_status='requested' and p_status in ('verifying','declined','expired','refunded'))
    or (old_status='verifying' and p_status in ('buyer_consent_pending','approved','declined','expired','refunded'))
    or (old_status='buyer_consent_pending' and p_status in ('approved','declined','expired','refunded'))
    or (old_status='approved' and p_status in ('introduced','declined','expired','refunded'));

  if not allowed then
    raise exception 'invalid_introduction_transition:%->%', old_status, p_status;
  end if;

  should_refund := p_status in ('declined','expired','refunded')
                   and req.credit_charged and not req.credit_refunded;

  if should_refund then
    update public.customer_entitlements
      set contact_credits_remaining=case when contact_credits_remaining is null then null else contact_credits_remaining+1 end,
          updated_at=now()
      where user_id=req.user_id;
  end if;

  update private.introduction_requests
    set status=p_status,
        reason=coalesce(p_reason,reason),
        updated_at=now(),
        approved_at=case when p_status='approved' and approved_at is null then now() else approved_at end,
        introduced_at=case when p_status='introduced' and introduced_at is null then now() else introduced_at end,
        credit_refunded=case when should_refund then true else credit_refunded end,
        refunded_at=case when should_refund and refunded_at is null then now() else refunded_at end
    where id=p_request_id
    returning * into req;

  insert into private.audit_log(opportunity_id,actor_id,event_type,details)
  values(req.opportunity_id,coalesce(nullif(p_actor,''),'service_role'),'introduction_status_changed',jsonb_build_object(
    'request_id',req.id,'from_status',old_status,'status',req.status,'reason',p_reason,'credit_refunded',should_refund
  ));

  return jsonb_build_object('ok',true,'request_id',req.id,'from_status',old_status,'status',req.status,'credit_refunded',req.credit_refunded);
end;
$$;

revoke all on function private.gb_apply_introduction_transition(uuid,text,text,text) from public,anon,authenticated;
grant execute on function private.gb_apply_introduction_transition(uuid,text,text,text) to service_role;

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
  jwt_role text := coalesce(current_setting('request.jwt.claim.role',true),'');
begin
  if jwt_role <> 'service_role' then raise exception 'service_role_required'; end if;
  return private.gb_apply_introduction_transition(p_request_id,p_status,p_reason,'service_role');
end;
$$;

revoke all on function public.set_introduction_status(uuid,text,text) from public,anon,authenticated;
grant execute on function public.set_introduction_status(uuid,text,text) to service_role;
