-- Read-only admin feed. The private table remains inaccessible to API roles.
create schema if not exists broker_internal;
revoke all on schema broker_internal from public, anon;
grant usage on schema broker_internal to authenticated;

create or replace function broker_internal.admin_opportunity_feed(p_limit integer default 500)
returns jsonb
language plpgsql stable security definer
set search_path = ''
as $$
declare result jsonb;
begin
  if auth.uid() is null or coalesce(auth.jwt()->>'aal','aal1') <> 'aal2' then
    raise exception 'admin_aal2_required' using errcode = '42501';
  end if;
  if not exists (select 1 from public.user_roles where user_id=auth.uid() and role='admin') then
    raise exception 'admin_role_required' using errcode = '42501';
  end if;
  select coalesce(jsonb_agg(t.opportunity order by t.updated_at desc, t.id),'[]'::jsonb)
  into result from (
    select id, opportunity, updated_at from private.opportunities
    order by updated_at desc,id limit greatest(1,least(coalesce(p_limit,500),500))
  ) t;
  return jsonb_build_object('opportunities',result,'count',jsonb_array_length(result),
                           'mode','admin_authenticated_private_feed');
end;
$$;
revoke all on function broker_internal.admin_opportunity_feed(integer) from public, anon, authenticated;
grant execute on function broker_internal.admin_opportunity_feed(integer) to authenticated;

-- Public API wrapper has no elevated table privileges. Its only operation calls
-- the narrowly granted private helper, which independently checks role and AAL2.
create or replace function public.gb_admin_opportunity_feed(p_limit integer default 500)
returns jsonb language sql stable security invoker
set search_path = ''
as $$ select broker_internal.admin_opportunity_feed(p_limit); $$;
revoke all on function public.gb_admin_opportunity_feed(integer) from public, anon, authenticated;
grant execute on function public.gb_admin_opportunity_feed(integer) to authenticated;
