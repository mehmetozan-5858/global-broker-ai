-- Review events never alter the submitted quote or approve a commercial deal.
create table if not exists private.quote_evidence_reviews (
  review_id uuid primary key,
  request_id uuid not null references private.quote_evidence_inbox(request_id),
  revision integer not null check (revision > 0),
  decision text not null check (decision in ('accepted_for_analysis','needs_information','rejected')),
  note text not null check (length(note) between 10 and 2000),
  checks jsonb not null,
  reviewed_by uuid not null,
  reviewed_at timestamptz not null default now(),
  unique (request_id,revision)
);
alter table private.quote_evidence_reviews enable row level security;
revoke all on private.quote_evidence_reviews from public,anon,authenticated;

create or replace function broker_internal.review_quote_evidence(p_review_id uuid,p_request_id uuid,p_expected_revision integer,p_decision text,p_note text,p_checks jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare q private.quote_evidence_inbox%rowtype; existing private.quote_evidence_reviews%rowtype; current_revision integer; k text;
begin
 perform broker_internal.quote_evidence_admin_check();
 if p_review_id is null or p_request_id is null or p_expected_revision is null or p_expected_revision<0
   or p_decision is null or p_decision not in ('accepted_for_analysis','needs_information','rejected')
   or p_note is null or length(btrim(p_note)) not between 10 and 2000
   or jsonb_typeof(p_checks) is distinct from 'object' then
   raise exception 'invalid_review' using errcode='22023';
 end if;
 if (select count(*) from jsonb_object_keys(p_checks))<>3 then raise exception 'invalid_checks' using errcode='22023'; end if;
 foreach k in array array['source_reviewed','identity_scope_checked','price_quantity_currency_checked'] loop
   if jsonb_typeof(p_checks->k) is distinct from 'boolean' then raise exception 'invalid_checks' using errcode='22023'; end if;
 end loop;
 select * into q from private.quote_evidence_inbox where request_id=p_request_id for update;
 if not found then raise exception 'quote_not_found' using errcode='22023'; end if;
 select * into existing from private.quote_evidence_reviews where review_id=p_review_id;
 if found then
   if existing.request_id<>p_request_id or existing.reviewed_by<>auth.uid() or existing.revision<>p_expected_revision+1
      or existing.decision<>p_decision or existing.note<>btrim(p_note) or existing.checks<>p_checks then
     raise exception 'review_request_conflict' using errcode='22023';
   end if;
   return jsonb_build_object('review_id',existing.review_id,'revision',existing.revision,'decision',existing.decision,'duplicate',true);
 end if;
 select coalesce(max(revision),0) into current_revision from private.quote_evidence_reviews where request_id=p_request_id;
 if current_revision<>p_expected_revision then raise exception 'review_changed_refresh_required' using errcode='40001'; end if;
 if p_decision='accepted_for_analysis' then
   if p_checks <> '{"source_reviewed":true,"identity_scope_checked":true,"price_quantity_currency_checked":true}'::jsonb
     or (q.quote->>'valid_until')::date<current_date
     or not exists(select 1 from private.opportunities where id=q.opportunity_id) then
     raise exception 'review_checks_or_current_quote_required' using errcode='22023';
   end if;
 end if;
 insert into private.quote_evidence_reviews(review_id,request_id,revision,decision,note,checks,reviewed_by)
 values(p_review_id,p_request_id,current_revision+1,p_decision,btrim(p_note),p_checks,auth.uid());
 return jsonb_build_object('review_id',p_review_id,'revision',current_revision+1,'decision',p_decision,'duplicate',false);
end; $$;
revoke all on function broker_internal.review_quote_evidence(uuid,uuid,integer,text,text,jsonb) from public,anon,authenticated;
grant execute on function broker_internal.review_quote_evidence(uuid,uuid,integer,text,text,jsonb) to authenticated;
create or replace function public.gb_review_quote_evidence(p_review_id uuid,p_request_id uuid,p_expected_revision integer,p_decision text,p_note text,p_checks jsonb)
returns jsonb language sql security invoker set search_path='' as $$
 select broker_internal.review_quote_evidence(p_review_id,p_request_id,p_expected_revision,p_decision,p_note,p_checks);
$$;
revoke all on function public.gb_review_quote_evidence(uuid,uuid,integer,text,text,jsonb) from public,anon,authenticated;
grant execute on function public.gb_review_quote_evidence(uuid,uuid,integer,text,text,jsonb) to authenticated;

create or replace function broker_internal.quote_evidence_workspace()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb; opportunities jsonb;
begin
 perform broker_internal.quote_evidence_admin_check();
 select coalesce(jsonb_agg(t.row),'[]'::jsonb) into opportunities from (
  select jsonb_build_object('id',id,'title',coalesce(opportunity->>'product_detail',opportunity->>'title_tr',opportunity->>'title_original',id)) as row
  from private.opportunities order by updated_at desc,id limit 500
 ) t;
 select coalesce(jsonb_agg(to_jsonb(t)),'[]'::jsonb) into result from (
  select q.request_id,q.opportunity_id,q.quote,q.submitted_at,q.status,r.review,
    (select count(*) from private.quote_evidence_reviews h where h.request_id=q.request_id) as review_count
  from private.quote_evidence_inbox q left join lateral (
   select jsonb_build_object('review_id',review_id,'revision',revision,'decision',decision,'note',note,'checks',checks,'reviewed_at',reviewed_at) as review
   from private.quote_evidence_reviews where request_id=q.request_id order by revision desc limit 1
  ) r on true order by q.submitted_at desc,q.request_id limit 50
 ) t;
 return jsonb_build_object('opportunities',opportunities,'quotes',result);
end; $$;

create or replace function broker_internal.quote_analysis_context(p_opportunity_id text)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare item jsonb; quotes jsonb; n integer;
begin
 perform broker_internal.quote_evidence_admin_check();
 select opportunity into item from private.opportunities where id=p_opportunity_id;
 if item is null then raise exception 'opportunity_not_found' using errcode='22023'; end if;
 select coalesce(jsonb_agg(jsonb_build_object('request_id',q.request_id,'quote',q.quote,'review',r.review)),'[]'::jsonb),count(*) into quotes,n
 from private.quote_evidence_inbox q join lateral (
  select decision,to_jsonb(v) as review from (
   select review_id,revision,decision,checks from private.quote_evidence_reviews where request_id=q.request_id order by revision desc limit 1
  ) v
 ) r on r.decision='accepted_for_analysis' where q.opportunity_id=p_opportunity_id;
 if n>100 then raise exception 'too_many_quotes_select_required' using errcode='22023'; end if;
 return jsonb_build_object('opportunity',item,'quotes',quotes);
end; $$;
revoke all on function broker_internal.quote_analysis_context(text) from public,anon,authenticated;
grant execute on function broker_internal.quote_analysis_context(text) to authenticated;
create or replace function public.gb_quote_analysis_context(p_opportunity_id text)
returns jsonb language sql stable security invoker set search_path='' as $$ select broker_internal.quote_analysis_context(p_opportunity_id); $$;
revoke all on function public.gb_quote_analysis_context(text) from public,anon,authenticated;
grant execute on function public.gb_quote_analysis_context(text) to authenticated;
