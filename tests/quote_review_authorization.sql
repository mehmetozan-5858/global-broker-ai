-- All synthetic quotes/reviews and assertions are rolled back.
begin;
select set_config('gb.test_admin',(select user_id::text from public.user_roles where role='admin' limit 1),true);
select set_config('gb.test_opportunity',(select id from private.opportunities limit 1),true);
set local role authenticated;
do $$
declare uid text:=current_setting('gb.test_admin'); oid text:=current_setting('gb.test_opportunity'); q jsonb; r jsonb; denied boolean;
 rid uuid:='22222222-2222-4222-8222-222222222222'; reviewid uuid:='33333333-3333-4333-8333-333333333333';
 checks jsonb:='{"source_reviewed":true,"identity_scope_checked":true,"price_quantity_currency_checked":true}';
begin
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'aal','aal1')::text,true);
 denied:=false;begin perform public.gb_review_quote_evidence(reviewid,rid,0,'accepted_for_analysis','SYNTHETIC review fixture',checks);exception when insufficient_privilege then denied:=true;end;
 assert denied,'aal1_cannot_review';
 perform set_config('request.jwt.claims',jsonb_build_object('sub','00000000-0000-4000-8000-000000000000','aal','aal2')::text,true);
 denied:=false;begin perform public.gb_quote_analysis_context(oid);exception when insufficient_privilege then denied:=true;end;
 assert denied,'nonadmin_cannot_analyze';
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'aal','aal2')::text,true);
 q:=jsonb_build_object('party','supplier','counterparty','SYNTHETIC ROLLBACK ONLY','reference','NOT-A-REAL-QUOTE',
 'quote_date',current_date::text,'valid_until',(current_date+7)::text,'amount','10.50','currency','USD','quantity','25','price_unit','piece','source_url','https://example.invalid/quote');
 perform public.gb_submit_quote_evidence(rid,oid,q);
 denied:=false;begin perform public.gb_review_quote_evidence(reviewid,rid,0,'accepted_for_analysis','SYNTHETIC review fixture',checks||'{"source_reviewed":false}');exception when invalid_parameter_value then denied:=true;end;
 assert denied,'acceptance_requires_all_checks';
 denied:=false;begin perform public.gb_review_quote_evidence(reviewid,rid,0,'approved','SYNTHETIC review fixture',checks);exception when invalid_parameter_value then denied:=true;end;
 assert denied,'commercial_approval_not_supported';
 r:=public.gb_review_quote_evidence(reviewid,rid,0,'accepted_for_analysis','SYNTHETIC review fixture',checks);
 assert r->>'revision'='1','first_review_revision';
 r:=public.gb_review_quote_evidence(reviewid,rid,0,'accepted_for_analysis','SYNTHETIC review fixture',checks);
 assert r->>'duplicate'='true','review_retry_idempotent';
 denied:=false;begin perform public.gb_review_quote_evidence(reviewid,rid,0,'rejected','SYNTHETIC changed retry',checks);exception when invalid_parameter_value then denied:=true;end;
 assert denied,'changed_retry_rejected';
 r:=public.gb_quote_analysis_context(oid);
 assert exists(select 1 from jsonb_array_elements(r->'quotes') x where x->>'request_id'=rid::text),'latest_accepted_review_reaches_analysis';
 denied:=false;begin perform public.gb_review_quote_evidence(gen_random_uuid(),rid,0,'rejected','SYNTHETIC stale decision',checks);exception when serialization_failure then denied:=true;end;
 assert denied,'stale_review_cannot_overwrite';
 r:=public.gb_review_quote_evidence(gen_random_uuid(),rid,1,'rejected','SYNTHETIC revoke evidence',checks);
 assert r->>'revision'='2','correction_is_new_event';
 r:=public.gb_quote_analysis_context(oid);
 assert not exists(select 1 from jsonb_array_elements(r->'quotes') x where x->>'request_id'=rid::text),'revoked_evidence_not_analyzed';
 r:=public.gb_quote_evidence_workspace();
 assert exists(select 1 from jsonb_array_elements(r->'quotes') x where x->>'request_id'=rid::text and x->>'review_count'='2' and x->'review'->>'decision'='rejected' and x->'quote'=q and x->>'status'='pending_review'),'audit_preserved_quote_immutable';
 perform public.gb_submit_quote_evidence('44444444-4444-4444-8444-444444444444',oid,q||jsonb_build_object('quote_date',(current_date-2)::text,'valid_until',(current_date-1)::text));
 denied:=false;begin perform public.gb_review_quote_evidence(gen_random_uuid(),'44444444-4444-4444-8444-444444444444',0,'accepted_for_analysis','SYNTHETIC expired evidence',checks);exception when invalid_parameter_value then denied:=true;end;
 assert denied,'expired_quote_cannot_be_accepted';
 denied:=false;begin perform 1 from private.quote_evidence_reviews;exception when insufficient_privilege then denied:=true;end;
 assert denied,'direct_review_table_denied';
end $$;
reset role;
set local role anon;
do $$ declare denied boolean:=false; begin
 begin perform public.gb_quote_analysis_context(current_setting('gb.test_opportunity'));exception when insufficient_privilege then denied:=true;end;
 assert denied,'anon_analysis_denied';
end $$;
reset role;
rollback;
