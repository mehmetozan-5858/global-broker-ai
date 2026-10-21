-- Synthetic users, intents and receipts are always rolled back.
begin;
insert into auth.users(id,email,email_confirmed_at) values
('99999999-1111-4111-8111-111111111111','billing-one@example.invalid',now()),
('99999999-2222-4222-8222-222222222222','billing-two@example.invalid',now());
select set_config('test.entitlement_count',(select count(*)::text from public.customer_entitlements),true);
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"99999999-1111-4111-8111-111111111111","role":"authenticated"}',true);
do $$declare r jsonb; i jsonb; denied boolean;
begin
 perform public.gb_request_membership('99999999-3333-4333-8333-333333333333','sector',true);
 i:=public.gb_prepare_sandbox_billing('99999999-3333-4333-8333-333333333333');
 assert i->>'amount_minor'='8900' and i->>'currency'='USD' and i->>'state'='prepared','trusted_catalog';
 perform set_config('test.intent_id',i->>'intent_id',true);
 r:=public.gb_prepare_sandbox_billing('99999999-3333-4333-8333-333333333333');assert r=i,'same_request_one_intent';
 denied:=false;begin perform public.gb_claim_sandbox_billing((i->>'intent_id')::uuid,'pri_'||repeat('0',26),'pro_'||repeat('0',26));exception when insufficient_privilege then denied:=true;end;assert denied,'owner_cannot_claim_provider';
 denied:=false;begin perform 1 from private.broker_sandbox_intents;exception when insufficient_privilege then denied:=true;end;assert denied,'direct_table_denied';
 perform set_config('request.jwt.claims','{"sub":"99999999-2222-4222-8222-222222222222","role":"authenticated"}',true);
 r:=public.gb_sandbox_billing_workspace();assert jsonb_array_length(r->'records')=0,'foreign_owner_cannot_list';
 denied:=false;begin perform public.gb_prepare_sandbox_billing('99999999-3333-4333-8333-333333333333');exception when insufficient_privilege then denied:=true;end;assert denied,'foreign_owner_cannot_claim';
end $$;
reset role;
set local role service_role;
select set_config('request.jwt.claims','{"role":"service_role"}',true);
do $$declare i uuid:=current_setting('test.intent_id')::uuid;r jsonb;c uuid;receipt jsonb;denied boolean;
begin
 r:=public.gb_claim_sandbox_billing(i,'pri_'||repeat('0',26),'pro_'||repeat('0',26));assert r->>'claimed'='true','first_creation_claim';c:=(r->>'claim_id')::uuid;
 r:=public.gb_claim_sandbox_billing(i,'pri_'||repeat('0',26),'pro_'||repeat('0',26));assert r->>'claimed'='false' and r->>'state'='creating','concurrent_retry_no_second_claim';
 denied:=false;begin perform public.gb_claim_sandbox_billing(i,'pri_'||repeat('1',26),'pro_'||repeat('0',26));exception when invalid_parameter_value then denied:=true;end;assert denied,'catalog_switch_rejected';
 denied:=false;begin perform public.gb_finish_sandbox_billing(i,gen_random_uuid(),'txn_'||repeat('0',26));exception when invalid_parameter_value then denied:=true;end;assert denied,'wrong_claim_rejected';
 perform public.gb_finish_sandbox_billing(i,c,'txn_'||repeat('0',26));
 r:=public.gb_claim_sandbox_billing(i,'pri_'||repeat('0',26),'pro_'||repeat('0',26));assert r->>'claimed'='false' and r->>'transaction_id'='txn_'||repeat('0',26),'created_transaction_reused';
 receipt:=jsonb_build_object('intent_id',i,'environment','sandbox','event_type','transaction.completed','event_id','evt_'||repeat('0',26),'transaction_id','txn_'||repeat('0',26),'price_id','pri_'||repeat('0',26),'product_id','pro_'||repeat('0',26),'amount_minor',8900,'currency','USD','event_at',now(),'projection_hash',repeat('a',64));
 denied:=false;begin perform public.gb_record_sandbox_billing(receipt||'{"amount_minor":1}'::jsonb);exception when invalid_parameter_value then denied:=true;end;assert denied,'amount_mismatch_rejected';
 denied:=false;begin perform public.gb_record_sandbox_billing(receipt||'{"environment":"live"}'::jsonb);exception when invalid_parameter_value then denied:=true;end;assert denied,'live_receipt_rejected';
 r:=public.gb_record_sandbox_billing(receipt);assert r->>'recorded'='true' and r->>'production_access_changed'='false','sandbox_recorded_without_entitlement';
 r:=public.gb_record_sandbox_billing(receipt);assert r->>'duplicate'='true','same_event_idempotent';
 denied:=false;begin perform public.gb_record_sandbox_billing(receipt||jsonb_build_object('projection_hash',repeat('b',64)));exception when invalid_parameter_value then denied:=true;end;assert denied,'changed_event_rejected';
 denied:=false;begin perform public.gb_record_sandbox_billing(receipt||jsonb_build_object('event_id','evt_'||repeat('1',26)));exception when invalid_parameter_value then denied:=true;end;assert denied,'second_receipt_rejected';
end $$;
reset role;
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"99999999-1111-4111-8111-111111111111","role":"authenticated"}',true);
do $$declare r jsonb;denied boolean;begin
 r:=public.gb_sandbox_billing_workspace();assert jsonb_array_length(r->'records')=1 and r->'records'->0->>'receipt_status'='sandbox_completed','owner_receipt_visible';
 assert not((r->'records'->0)?'user_id') and not((r->'records'->0)?'transaction_id') and not((r->'records'->0)?'claim_id'),'private_projection';
 denied:=false;begin perform public.gb_record_sandbox_billing('{}');exception when insufficient_privilege then denied:=true;end;assert denied,'browser_cannot_record_receipt';
 perform set_config('request.jwt.claims','{"sub":"99999999-2222-4222-8222-222222222222","role":"authenticated"}',true);
 assert jsonb_array_length(public.gb_sandbox_billing_workspace()->'records')=0,'other_owner_still_empty';
end $$;
reset role;
set local role anon;
do $$declare denied boolean;begin
 denied:=false;begin perform public.gb_sandbox_billing_workspace();exception when insufficient_privilege then denied:=true;end;assert denied,'anonymous_denied';
 denied:=false;begin perform public.gb_record_sandbox_billing('{}');exception when insufficient_privilege then denied:=true;end;assert denied,'anonymous_record_denied';
end $$;
reset role;
do $$begin
 assert (select count(*) from public.customer_entitlements)=current_setting('test.entitlement_count')::integer,'real_entitlements_unchanged';
end $$;
rollback;
