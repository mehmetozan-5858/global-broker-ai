-- Synthetic freight checks are rolled back, including review events.
begin;
select set_config('gb.test_admin',(select user_id::text from public.user_roles where role='admin' limit 1),true);
select set_config('gb.test_opportunity',(select id from private.opportunities limit 1),true);
set local role authenticated;
do $$
declare q jsonb; r jsonb; denied boolean; oid text:=current_setting('gb.test_opportunity');
 rid uuid:='55555555-5555-4555-8555-555555555555';
 checks jsonb:='{"source_reviewed":true,"identity_scope_checked":true,"price_quantity_currency_checked":true}';
begin
 perform set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('gb.test_admin'),'aal','aal1')::text,true);
 denied:=false;begin perform public.gb_submit_quote_evidence(rid,oid,'{}');exception when insufficient_privilege then denied:=true;end;
 assert denied,'freight_requires_admin_aal2';
 perform set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('gb.test_admin'),'aal','aal2')::text,true);
 q:=jsonb_build_object('party','freight','counterparty','SYNTHETIC ROLLBACK ONLY','reference','NOT-REAL','quote_date',current_date::text,'valid_until',(current_date+7)::text,'amount','250','currency','USD','quantity','100','price_unit','piece','source_url','https://example.invalid/freight','origin','Fixture A','destination','Fixture B','incoterm','DAP','transport_mode','road','amount_basis','shipment_total');
 denied:=false;begin perform public.gb_submit_quote_evidence(rid,oid,q||'{"amount_basis":"unit"}');exception when invalid_parameter_value then denied:=true;end;
 assert denied,'freight_must_be_shipment_total';
 denied:=false;begin perform public.gb_submit_quote_evidence(rid,oid,q||'{"destination":"fixture a"}');exception when invalid_parameter_value then denied:=true;end;
 assert denied,'route_endpoints_must_differ';
 denied:=false;begin perform public.gb_submit_quote_evidence(rid,oid,q-'origin');exception when invalid_parameter_value then denied:=true;end;
 assert denied,'route_required';
 perform public.gb_submit_quote_evidence(rid,oid,q);
 r:=public.gb_submit_quote_evidence(rid,oid,q);assert r->>'duplicate'='true','retry_is_idempotent';
 perform public.gb_review_quote_evidence(gen_random_uuid(),rid,0,'accepted_for_analysis','SYNTHETIC freight review only',checks);
 r:=public.gb_quote_analysis_context(oid);
 assert exists(select 1 from jsonb_array_elements(r->'quotes') x where x->>'request_id'=rid::text and x->'quote'=q),'reviewed_freight_preserves_scope';
end $$;
reset role;
rollback;
