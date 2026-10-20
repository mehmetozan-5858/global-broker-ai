-- Synthetic evidence is inserted only within this rolled-back transaction.
begin;
do $$ begin
  perform set_config('gb.test_admin',(select user_id::text from public.user_roles where role='admin' limit 1),true);
  perform set_config('gb.test_opportunity',(select id from private.opportunities limit 1),true);
  perform set_config('request.jwt.claims','{}',true);
end $$;
set local role authenticated;
do $$
declare q jsonb; r jsonb; denied boolean; uid text:=current_setting('gb.test_admin'); oid text:=current_setting('gb.test_opportunity');
rid uuid:='11111111-1111-4111-8111-111111111111';
begin
  denied:=false;
  begin perform public.gb_quote_evidence_workspace(); exception when insufficient_privilege then denied:=true; end;
  assert denied,'anonymous_claims_rejected';
  perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'aal','aal1')::text,true);
  denied:=false;
  begin perform public.gb_quote_evidence_workspace(); exception when insufficient_privilege then denied:=true; end;
  assert denied,'aal1_rejected';
  perform set_config('request.jwt.claims',jsonb_build_object('sub','00000000-0000-4000-8000-000000000000','aal','aal2')::text,true);
  denied:=false;
  begin perform public.gb_quote_evidence_workspace(); exception when insufficient_privilege then denied:=true; end;
  assert denied,'nonadmin_rejected';
  perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'aal','aal2')::text,true);
  r:=public.gb_quote_evidence_workspace();
  assert jsonb_typeof(r->'opportunities')='array','admin_workspace';
  q:=jsonb_build_object('party','supplier','counterparty','SYNTHETIC ROLLBACK TEST','reference','FIXTURE-NOT-A-REAL-QUOTE',
    'quote_date',current_date::text,'valid_until',(current_date+7)::text,'amount','10.50','currency','USD',
    'quantity','25','price_unit','piece','source_url','https://example.invalid/quote');
  r:=public.gb_submit_quote_evidence(rid,oid,q);
  assert r->>'status'='pending_review','submission_never_approves';
  r:=public.gb_submit_quote_evidence(rid,oid,q);
  assert r->>'duplicate'='true','retry_deduplicated';
  r:=public.gb_quote_evidence_workspace();
  assert (select count(*) from jsonb_array_elements(r->'quotes') x where x->>'request_id'=rid::text)=1,'one_persisted_record';
  denied:=false;
  begin perform public.gb_submit_quote_evidence(rid,oid,q||'{"amount":"12"}'::jsonb); exception when invalid_parameter_value then denied:=true; end;
  assert denied,'changed_retry_rejected';
  denied:=false;
  begin perform public.gb_submit_quote_evidence(gen_random_uuid(),'fixture-opportunity-does-not-exist',q); exception when invalid_parameter_value then denied:=true; end;
  assert denied,'wrong_opportunity_rejected';
  denied:=false;
  begin perform public.gb_submit_quote_evidence(gen_random_uuid(),oid,q||'{"amount":"0"}'::jsonb); exception when invalid_parameter_value then denied:=true; end;
  assert denied,'zero_price_rejected';
  denied:=false;
  begin perform public.gb_submit_quote_evidence(gen_random_uuid(),oid,q||'{"source_url":"https://user:secret@example.invalid/quote"}'::jsonb); exception when invalid_parameter_value then denied:=true; end;
  assert denied,'credential_url_rejected';
  denied:=false;
  begin perform public.gb_submit_quote_evidence(gen_random_uuid(),oid,q||'{"verified":true}'::jsonb); exception when invalid_parameter_value then denied:=true; end;
  assert denied,'client_approval_rejected';
  denied:=false;
  begin perform 1 from private.quote_evidence_inbox; exception when insufficient_privilege then denied:=true; end;
  assert denied,'direct_table_rejected';
end $$;
reset role;
set local role anon;
do $$ declare denied boolean:=false; begin
  begin perform public.gb_quote_evidence_workspace(); exception when insufficient_privilege then denied:=true; end;
  assert denied,'anon_execute_rejected';
end $$;
reset role;
rollback;
