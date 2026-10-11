-- Global Broker automated introduction verification agent.
-- This agent never reveals raw contact details. It classifies the safest next step.
-- Authorization is enforced by EXECUTE grants: only service_role can call these RPCs.

alter table private.introduction_requests
  add column if not exists verification_route_type text,
  add column if not exists verification_score integer,
  add column if not exists verification_checked_at timestamptz,
  add column if not exists buyer_consent_required boolean;

create or replace function public.gb_verify_introduction_request(p_request_id uuid)
returns jsonb
language plpgsql
security definer
set search_path=public,private,auth
as $$
declare
  req private.introduction_requests%rowtype;
  opp jsonb;
  goods_ok boolean := false;
  contact_backed boolean := false;
  buyer_backed boolean := false;
  public_procurement boolean := false;
  route_type text;
  score integer := 0;
  next_status text;
  reason_text text;
  source_text text;
  email text;
  phone text;
  website text;
  source_url text;
  refund_now boolean := false;
begin
  select * into req from private.introduction_requests where id=p_request_id for update;
  if not found then raise exception 'introduction_request_not_found'; end if;

  if req.status not in ('requested','verifying') then
    return jsonb_build_object('ok',true,'request_id',req.id,'status',req.status,'skipped',true);
  end if;

  update private.introduction_requests set status='verifying',updated_at=now() where id=req.id;

  select opportunity into opp from private.opportunities where id=req.opportunity_id;
  if opp is null then
    next_status := 'declined';
    reason_text := 'opportunity_not_available';
  else
    goods_ok := coalesce(opp #>> '{export_goods_review,status}','')='goods_candidate';
    contact_backed := coalesce((opp->>'contact_source_backed')::boolean,false);
    buyer_backed := coalesce(opp #>> '{field_evidence,buyer,status}','')='source_backed'
                    or lower(coalesce(opp #>> '{buyer_verification,status}','')) in ('verified','source_backed');

    email := case when contact_backed then coalesce(nullif(opp->>'contact_email',''),nullif(opp->>'buyer_email',''),nullif(opp->>'email_address','')) end;
    phone := case when contact_backed then coalesce(nullif(opp->>'contact_phone',''),nullif(opp->>'buyer_phone',''),nullif(opp->>'phone_number','')) end;
    website := case when contact_backed then coalesce(nullif(opp->>'buyer_website',''),nullif(opp->>'organization_url',''),nullif(opp->>'website','')) end;
    source_url := coalesce(nullif(opp->>'source_url',''),nullif(opp->>'source-url',''),nullif(opp->>'notice_url',''),nullif(opp->>'detail_url',''),nullif(opp->>'url',''),nullif(opp->>'document_url',''));

    if website is not null and website !~* '^https://' then website := null; end if;
    if source_url is not null and source_url !~* '^https://' then source_url := null; end if;

    if email is not null or phone is not null then route_type := 'direct_contact';
    elsif website is not null then route_type := 'verified_web';
    elsif source_url is not null then route_type := 'official_source_route';
    else route_type := null;
    end if;

    source_text := lower(concat_ws(' ',opp->>'source',opp->>'source_name',opp->>'source_type',opp->>'portal_family',opp->>'notice_type',opp->>'procurement_method'));
    public_procurement := source_text ~ '(ted|sam\.gov|world bank|etimad|monaqasat|ggzy|procurement|tender|ihale|public notice|contract notice)';

    if buyer_backed then score := score + 25; end if;
    if route_type='direct_contact' then score := score + 45;
    elsif route_type='verified_web' then score := score + 30;
    elsif route_type='official_source_route' then score := score + 20;
    end if;
    if source_url is not null then score := score + 15; end if;
    if public_procurement then score := score + 15; end if;
    score := least(score,100);

    if not goods_ok then
      next_status := 'declined'; reason_text := 'not_verified_physical_goods';
    elsif route_type is null then
      next_status := 'declined'; reason_text := 'no_verified_access_route';
    elsif public_procurement then
      next_status := 'approved'; reason_text := 'official_public_procurement_route_verified';
    elsif buyer_backed and route_type in ('direct_contact','verified_web') then
      next_status := 'buyer_consent_pending'; reason_text := 'verified_private_buyer_requires_consent';
    else
      next_status := 'verifying'; reason_text := 'manual_broker_review_required';
    end if;
  end if;

  refund_now := next_status='declined' and req.credit_charged and not req.credit_refunded;
  if refund_now then
    update public.customer_entitlements
      set contact_credits_remaining=case when contact_credits_remaining is null then null else contact_credits_remaining+1 end,
          updated_at=now()
      where user_id=req.user_id;
  end if;

  update private.introduction_requests
    set status=next_status,
        reason=reason_text,
        verification_route_type=route_type,
        verification_score=score,
        verification_checked_at=now(),
        buyer_consent_required=(next_status='buyer_consent_pending'),
        approved_at=case when next_status='approved' then now() else approved_at end,
        credit_refunded=case when refund_now then true else credit_refunded end,
        refunded_at=case when refund_now then now() else refunded_at end,
        updated_at=now()
    where id=req.id;

  insert into private.audit_log(opportunity_id,actor_id,event_type,details)
  values(req.opportunity_id,'verification_agent','introduction_verified',jsonb_build_object(
    'request_id',req.id,'status',next_status,'route_type',route_type,'score',score,
    'reason',reason_text,'credit_refunded',refund_now
  ));

  return jsonb_build_object('ok',true,'request_id',req.id,'status',next_status,'route_type',route_type,'verification_score',score,'reason',reason_text,'credit_refunded',refund_now);
end;
$$;

create or replace function public.gb_process_introduction_queue(p_limit integer default 25)
returns jsonb
language plpgsql
security definer
set search_path=public,private,auth
as $$
declare
  r record;
  result jsonb;
  processed integer := 0;
  approved integer := 0;
  consent_pending integer := 0;
  declined integer := 0;
  verifying integer := 0;
begin
  if p_limit is null or p_limit < 1 or p_limit > 100 then raise exception 'invalid_queue_limit'; end if;

  for r in
    select id from private.introduction_requests
    where status in ('requested','verifying')
    order by requested_at asc
    limit p_limit
  loop
    result := public.gb_verify_introduction_request(r.id);
    processed := processed + 1;
    case result->>'status'
      when 'approved' then approved := approved + 1;
      when 'buyer_consent_pending' then consent_pending := consent_pending + 1;
      when 'declined' then declined := declined + 1;
      else verifying := verifying + 1;
    end case;
  end loop;

  return jsonb_build_object('ok',true,'processed',processed,'approved',approved,'buyer_consent_pending',consent_pending,'declined',declined,'verifying',verifying);
end;
$$;

revoke all on function public.gb_verify_introduction_request(uuid) from public,anon,authenticated;
grant execute on function public.gb_verify_introduction_request(uuid) to service_role;
revoke all on function public.gb_process_introduction_queue(integer) from public,anon,authenticated;
grant execute on function public.gb_process_introduction_queue(integer) to service_role;
