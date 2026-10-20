-- All synthetic membership requests and users are rolled back.
begin;
insert into auth.users(id,email,email_confirmed_at) values
('77777777-7777-4777-8777-777777777771','membership-one@example.invalid',now()),
('77777777-7777-4777-8777-777777777772','membership-two@example.invalid',now()),
('77777777-7777-4777-8777-777777777773','membership-unverified@example.invalid',null);
set local role authenticated;
do $$
declare r jsonb; denied boolean; before_plan text; request uuid:='88888888-8888-4888-8888-888888888881';
begin
 perform set_config('request.jwt.claims','{"sub":"77777777-7777-4777-8777-777777777773"}',true);
 denied:=false;begin perform public.gb_membership_workspace();exception when insufficient_privilege then denied:=true;end;assert denied,'unverified_email_rejected';
 perform set_config('request.jwt.claims','{"sub":"77777777-7777-4777-8777-777777777771"}',true);
 r:=public.gb_membership_workspace();before_plan:=r->>'current_plan';
 assert r->>'checkout_enabled'='false' and jsonb_array_length(r->'requests')=0,'checkout_stays_closed';
 denied:=false;begin perform public.gb_request_membership(request,'global',false);exception when invalid_parameter_value then denied:=true;end;assert denied,'explicit_acknowledgement_required';
 denied:=false;begin perform public.gb_request_membership(request,'enterprise',true);exception when invalid_parameter_value then denied:=true;end;assert denied,'custom_price_plan_not_orderable';
 perform public.gb_request_membership(request,'global',true);
 r:=public.gb_request_membership(request,'global',true);assert r->>'duplicate'='true','same_id_retry';
 r:=public.gb_request_membership(gen_random_uuid(),'global',true);assert r->>'request_id'=request::text,'same_plan_not_duplicated';
 denied:=false;begin perform public.gb_request_membership(request,'sector',true);exception when invalid_parameter_value then denied:=true;end;assert denied,'changed_retry_rejected';
 r:=public.gb_membership_workspace();assert r->>'current_plan'=before_plan,'request_never_changes_entitlement';
 assert jsonb_array_length(r->'requests')=1 and r->'requests'->0->>'amount_minor'='34900' and r->'requests'->0->>'currency'='USD','server_catalog_price';
 assert r->'requests'->0->>'invoice_status'='not_issued' and not(r->'requests'->0 ? 'user_id'),'not_invoice_and_no_owner_id';
 denied:=false;begin perform 1 from private.membership_requests;exception when insufficient_privilege then denied:=true;end;assert denied,'direct_table_denied';
 perform set_config('request.jwt.claims','{"sub":"77777777-7777-4777-8777-777777777772"}',true);
 r:=public.gb_membership_workspace();assert jsonb_array_length(r->'requests')=0,'other_owner_cannot_list';
 denied:=false;begin perform public.gb_request_membership(request,'global',true);exception when invalid_parameter_value then denied:=true;end;assert denied,'other_owner_cannot_replay';
 perform public.gb_request_membership(gen_random_uuid(),'multi',true);
 r:=public.gb_membership_workspace();assert jsonb_array_length(r->'requests')=1 and r->'requests'->0->>'plan_id'='multi','other_owner_gets_only_own_request';
end $$;
reset role;
set local role anon;
do $$ declare denied boolean:=false;begin
 begin perform public.gb_membership_workspace();exception when insufficient_privilege then denied:=true;end;assert denied,'anonymous_list_denied';
end $$;
reset role;
rollback;
