-- Global Broker secure private contact unlock v2.
-- Contact disclosure, entitlement checks and credit debit happen atomically in Supabase.
-- No private contact is read from the public masked feed.

create or replace function public.unlock_opportunity_contact(p_opportunity_id text)
returns jsonb
language plpgsql
security definer
set search_path=public,private,auth
as $$
declare
  uid uuid := auth.uid();
  ent public.customer_entitlements%rowtype;
  pref public.customer_preferences%rowtype;
  opp jsonb;
  sector_id text;
  country_code text;
  already boolean;
  buyer_name text;
  contact_person text;
  email text;
  phone text;
  website text;
  source_url text;
  route_type text;
  quality_score integer := 0;
  quality_level text;
  remaining integer;
  contact jsonb;
begin
  if uid is null then raise exception 'authentication_required'; end if;
  if p_opportunity_id is null or length(trim(p_opportunity_id)) < 8 or length(p_opportunity_id) > 200 then
    raise exception 'invalid_opportunity_id';
  end if;

  select * into ent from public.customer_entitlements
  where user_id=uid and active=true for update;
  if not found then raise exception 'active_plan_required'; end if;

  select * into pref from public.customer_preferences where user_id=uid;
  if not found then
    pref.user_id := uid;
    pref.selected_sectors := '{}'::text[];
    pref.selected_countries := '{}'::text[];
  end if;

  select opportunity into opp from private.opportunities where id=p_opportunity_id;
  if opp is null then raise exception 'opportunity_not_found'; end if;

  sector_id := coalesce(opp->>'sector_id',opp->>'sector','');
  country_code := upper(coalesce(opp->>'country_code',opp->>'buyer_country_code',''));

  if not ent.all_sectors and not (sector_id = any(coalesce(pref.selected_sectors,'{}'::text[]))) then
    raise exception 'sector_not_in_plan';
  end if;
  if coalesce(array_length(pref.selected_countries,1),0) > 0
     and (country_code = '' or not (country_code = any(pref.selected_countries))) then
    raise exception 'country_not_selected';
  end if;

  buyer_name := coalesce(
    nullif(opp #>> '{field_evidence,buyer,value}',''),
    nullif(opp->>'buyer-name',''),nullif(opp->>'buyer_name',''),nullif(opp->>'borrower',''),
    nullif(opp->>'agency',''),nullif(opp->>'department',''),nullif(opp->>'office',''),
    nullif(opp->>'contracting_authority',''),nullif(opp->>'organization_name','')
  );

  if coalesce((opp->>'contact_source_backed')::boolean,false) then
    contact_person := coalesce(nullif(opp->>'contact_person',''),nullif(opp->>'representative',''),nullif(opp->>'contact_name',''));
    email := coalesce(nullif(opp->>'contact_email',''),nullif(opp->>'buyer_email',''),nullif(opp->>'email_address',''));
    phone := coalesce(nullif(opp->>'contact_phone',''),nullif(opp->>'buyer_phone',''),nullif(opp->>'phone_number',''));
    website := coalesce(nullif(opp->>'buyer_website',''),nullif(opp->>'organization_url',''),nullif(opp->>'website',''));
  end if;

  source_url := coalesce(
    nullif(opp->>'source_url',''),nullif(opp->>'source-url',''),nullif(opp->>'notice_url',''),
    nullif(opp->>'detail_url',''),nullif(opp->>'url',''),nullif(opp->>'document_url','')
  );

  if website is not null and website !~* '^https://' then website := null; end if;
  if source_url is not null and source_url !~* '^https://' then source_url := null; end if;

  if email is not null or phone is not null then route_type := 'direct_contact';
  elsif website is not null then route_type := 'verified_web';
  elsif source_url is not null then route_type := 'official_source_route';
  else raise exception 'contact_not_available';
  end if;

  if buyer_name is not null then quality_score := quality_score + 15; end if;
  if email is not null then quality_score := quality_score + 35; end if;
  if phone is not null then quality_score := quality_score + 25; end if;
  if website is not null then quality_score := quality_score + 15; end if;
  if contact_person is not null then quality_score := quality_score + 10; end if;
  if source_url is not null then quality_score := quality_score + 15; end if;
  quality_score := least(100, quality_score);
  quality_level := case when quality_score >= 75 then 'A' when quality_score >= 55 then 'B' when quality_score >= 35 then 'C' else 'D' end;

  contact := jsonb_strip_nulls(jsonb_build_object(
    'buyer_name',buyer_name,'contact_person',contact_person,'email',email,'phone',phone,
    'website',website,'source_url',source_url
  ));

  select exists(select 1 from private.contact_unlocks where user_id=uid and opportunity_id=p_opportunity_id) into already;
  if already then
    return jsonb_build_object(
      'ok',true,'already_unlocked',true,'credits_remaining',ent.contact_credits_remaining,
      'route_type',route_type,'quality_score',quality_score,'quality_level',quality_level,'contact',contact
    );
  end if;

  if ent.contact_credits_remaining is not null and ent.contact_credits_remaining <= 0 then
    raise exception 'contact_credit_required';
  end if;

  insert into private.contact_unlocks(user_id,opportunity_id) values(uid,p_opportunity_id);
  if ent.contact_credits_remaining is not null then
    update public.customer_entitlements
    set contact_credits_remaining=contact_credits_remaining-1,updated_at=now()
    where user_id=uid returning contact_credits_remaining into remaining;
  else
    remaining := null;
  end if;

  insert into private.audit_log(opportunity_id,actor_id,event_type,details)
  values(p_opportunity_id,uid::text,'contact_unlocked',jsonb_build_object(
    'plan_id',ent.plan_id,'route_type',route_type,'quality_score',quality_score,'quality_level',quality_level
  ));

  return jsonb_build_object(
    'ok',true,'already_unlocked',false,'credits_remaining',remaining,
    'route_type',route_type,'quality_score',quality_score,'quality_level',quality_level,'contact',contact
  );
end;
$$;

revoke all on function public.unlock_opportunity_contact(text) from public, anon;
grant execute on function public.unlock_opportunity_contact(text) to authenticated;
