-- Extend immutable evidence intake; freight amount is the whole shipment total.
create or replace function broker_internal.submit_quote_evidence(p_request_id uuid,p_opportunity_id text,p_quote jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare q jsonb; stored private.quote_evidence_inbox%rowtype; k text; freight boolean; fields text[];
begin
  perform broker_internal.quote_evidence_admin_check();
  if p_request_id is null or p_opportunity_id is null or length(p_opportunity_id)>200
     or jsonb_typeof(p_quote) is distinct from 'object' or octet_length(p_quote::text)>6000 then
    raise exception 'invalid_quote' using errcode='22023';
  end if;
  freight := coalesce(p_quote->>'party','')='freight';
  fields := array['party','counterparty','reference','quote_date','valid_until','amount','currency','quantity','price_unit','source_url'];
  if freight then fields := fields || array['origin','destination','incoterm','transport_mode','amount_basis']; end if;
  q := '{}'::jsonb;
  foreach k in array fields loop
    if jsonb_typeof(p_quote->k) is distinct from 'string' or length(btrim(p_quote->>k)) not between 1 and 500 then
      raise exception 'quote_field_required' using errcode='22023';
    end if;
    q := q || jsonb_build_object(k,btrim(p_quote->>k));
  end loop;
  if (select count(*) from jsonb_object_keys(p_quote))<>cardinality(fields)
    or q->>'party' not in ('supplier','buyer','freight')
    or q->>'currency' !~ '^[A-Z]{3}$'
    or q->>'amount' !~ '^[0-9]{1,12}(\.[0-9]{1,6})?$'
    or q->>'quantity' !~ '^[0-9]{1,12}(\.[0-9]{1,6})?$'
    or (q->>'amount')::numeric<=0 or (q->>'quantity')::numeric<=0
    or q->>'quote_date' !~ '^\d{4}-\d{2}-\d{2}$'
    or q->>'valid_until' !~ '^\d{4}-\d{2}-\d{2}$'
    or (q->>'quote_date')::date>current_date
    or (q->>'valid_until')::date<(q->>'quote_date')::date
    or q->>'source_url' !~ '^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?(/|$)'
    or q->>'source_url' ~ '[[:space:]]' then
    raise exception 'invalid_quote_fields' using errcode='22023';
  end if;
  if freight and (q->>'amount_basis'<>'shipment_total'
    or q->>'incoterm' not in ('EXW','FCA','FAS','FOB','CFR','CIF','CPT','CIP','DAP','DPU','DDP')
    or q->>'transport_mode' not in ('road','sea','air','rail','multimodal')
    or lower(q->>'origin')=lower(q->>'destination')) then
    raise exception 'invalid_freight_scope' using errcode='22023';
  end if;
  -- Retries remain idempotent even if a later source scan archives this notice.
  select * into stored from private.quote_evidence_inbox where request_id=p_request_id;
  if found then
    if stored.submitted_by<>auth.uid() or stored.opportunity_id<>p_opportunity_id or stored.quote<>q then
      raise exception 'request_conflict' using errcode='22023';
    end if;
    return jsonb_build_object('request_id',stored.request_id,'status',stored.status,'duplicate',true);
  end if;
  if not exists(select 1 from private.opportunities where id=p_opportunity_id) then
    raise exception 'opportunity_not_found' using errcode='22023';
  end if;
  insert into private.quote_evidence_inbox(request_id,opportunity_id,quote,submitted_by)
  values(p_request_id,p_opportunity_id,q,auth.uid()) on conflict(request_id) do nothing;
  select * into stored from private.quote_evidence_inbox where request_id=p_request_id;
  if stored.submitted_by<>auth.uid() or stored.opportunity_id<>p_opportunity_id or stored.quote<>q then
    raise exception 'request_conflict' using errcode='22023';
  end if;
  return jsonb_build_object('request_id',stored.request_id,'status',stored.status);
end; $$;
revoke all on function broker_internal.submit_quote_evidence(uuid,text,jsonb) from public, anon, authenticated;
grant execute on function broker_internal.submit_quote_evidence(uuid,text,jsonb) to authenticated;

