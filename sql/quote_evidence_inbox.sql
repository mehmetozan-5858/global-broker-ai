-- Private, append-only submitted quotes. Submission never verifies a price.
create table if not exists private.quote_evidence_inbox (
  request_id uuid primary key,
  opportunity_id text not null,
  quote jsonb not null,
  submitted_by uuid not null,
  submitted_at timestamptz not null default now(),
  status text not null default 'pending_review' check (status = 'pending_review')
);
create index if not exists quote_evidence_inbox_recent on private.quote_evidence_inbox(submitted_at desc);
create index if not exists quote_evidence_inbox_opportunity on private.quote_evidence_inbox(opportunity_id);
alter table private.quote_evidence_inbox enable row level security;
revoke all on private.quote_evidence_inbox from public, anon, authenticated;

create or replace function broker_internal.quote_evidence_admin_check()
returns void language plpgsql stable security definer set search_path = '' as $$
begin
  if auth.uid() is null or coalesce(auth.jwt()->>'aal','aal1') <> 'aal2'
    or not exists (select 1 from public.user_roles r join auth.users u on u.id=r.user_id
                   where r.user_id=auth.uid() and r.role='admin') then
    raise exception 'admin_aal2_required' using errcode='42501';
  end if;
end; $$;
revoke all on function broker_internal.quote_evidence_admin_check() from public, anon, authenticated;

create or replace function broker_internal.quote_evidence_workspace()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare result jsonb; opportunities jsonb;
begin
  perform broker_internal.quote_evidence_admin_check();
  select coalesce(jsonb_agg(t.row),'[]'::jsonb) into opportunities from (
    select jsonb_build_object('id',id,'title',coalesce(opportunity->>'product_detail',opportunity->>'title_tr',opportunity->>'title_original',id)) as row
    from private.opportunities order by updated_at desc,id limit 500
  ) t;
  select coalesce(jsonb_agg(to_jsonb(t)),'[]'::jsonb) into result from (
    select request_id,opportunity_id,quote,submitted_at,status from private.quote_evidence_inbox
    order by submitted_at desc,request_id limit 50
  ) t;
  return jsonb_build_object('opportunities',opportunities,'quotes',result);
end; $$;
revoke all on function broker_internal.quote_evidence_workspace() from public, anon, authenticated;
grant execute on function broker_internal.quote_evidence_workspace() to authenticated;

create or replace function broker_internal.submit_quote_evidence(p_request_id uuid,p_opportunity_id text,p_quote jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare q jsonb; stored private.quote_evidence_inbox%rowtype; k text;
begin
  perform broker_internal.quote_evidence_admin_check();
  if p_request_id is null or p_opportunity_id is null or length(p_opportunity_id)>200
     or jsonb_typeof(p_quote) is distinct from 'object' or octet_length(p_quote::text)>6000 then
    raise exception 'invalid_quote' using errcode='22023';
  end if;
  q := '{}'::jsonb;
  foreach k in array array['party','counterparty','reference','quote_date','valid_until','amount','currency','quantity','price_unit','source_url'] loop
    if jsonb_typeof(p_quote->k) is distinct from 'string' or length(btrim(p_quote->>k)) not between 1 and 500 then
      raise exception 'quote_field_required' using errcode='22023';
    end if;
    q := q || jsonb_build_object(k,btrim(p_quote->>k));
  end loop;
  if (select count(*) from jsonb_object_keys(p_quote))<>10
    or q->>'party' not in ('supplier','buyer')
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

create or replace function public.gb_quote_evidence_workspace()
returns jsonb language sql stable security invoker set search_path = ''
as $$ select broker_internal.quote_evidence_workspace(); $$;
create or replace function public.gb_submit_quote_evidence(p_request_id uuid,p_opportunity_id text,p_quote jsonb)
returns jsonb language sql security invoker set search_path = ''
as $$ select broker_internal.submit_quote_evidence(p_request_id,p_opportunity_id,p_quote); $$;
revoke all on function public.gb_quote_evidence_workspace() from public, anon, authenticated;
revoke all on function public.gb_submit_quote_evidence(uuid,text,jsonb) from public, anon, authenticated;
grant execute on function public.gb_quote_evidence_workspace() to authenticated;
grant execute on function public.gb_submit_quote_evidence(uuid,text,jsonb) to authenticated;
