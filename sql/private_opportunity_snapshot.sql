-- Keep the private opportunity store aligned to the latest validated snapshot.
-- Stale rows are archived instead of silently accumulating. Rows referenced by
-- introduction history are preserved in the active table for traceability.

create table if not exists private.opportunity_archive (
  id text not null,
  opportunity jsonb not null,
  archived_at timestamptz not null default now(),
  archive_reason text not null default 'stale_snapshot',
  primary key (id, archived_at)
);

alter table private.opportunity_archive enable row level security;

create or replace function public.gb_replace_private_opportunities(p_rows jsonb)
returns jsonb
language plpgsql
security definer
set search_path=public,private,auth
as $$
declare
  item jsonb;
  oid text;
  incoming_ids text[] := '{}'::text[];
  upserted integer := 0;
  archived integer := 0;
  preserved integer := 0;
begin
  if jsonb_typeof(p_rows) <> 'array' then raise exception 'rows_must_be_array'; end if;
  if jsonb_array_length(p_rows) = 0 then raise exception 'empty_snapshot_refused'; end if;

  for item in select value from jsonb_array_elements(p_rows) loop
    oid := left(coalesce(item->>'opportunity_id', item->>'id',''),200);
    if oid = '' then raise exception 'missing_opportunity_id'; end if;
    if oid = any(incoming_ids) then raise exception 'duplicate_opportunity_id'; end if;
    incoming_ids := array_append(incoming_ids, oid);
    insert into private.opportunities(id,opportunity,updated_at)
    values(oid,item,now())
    on conflict(id) do update set opportunity=excluded.opportunity,updated_at=now();
    upserted := upserted + 1;
  end loop;

  insert into private.opportunity_archive(id,opportunity,archived_at,archive_reason)
  select p.id,p.opportunity,now(),'stale_snapshot'
  from private.opportunities p
  where not (p.id = any(incoming_ids))
    and not exists (
      select 1 from private.introduction_requests r
      where r.opportunity_id=p.id
    );
  get diagnostics archived = row_count;

  delete from private.opportunities p
  where not (p.id = any(incoming_ids))
    and not exists (
      select 1 from private.introduction_requests r
      where r.opportunity_id=p.id
    );

  select count(*) into preserved
  from private.opportunities p
  where not (p.id = any(incoming_ids));

  return jsonb_build_object(
    'ok',true,
    'upserted',upserted,
    'archived_stale',archived,
    'preserved_referenced',preserved,
    'active_count',(select count(*) from private.opportunities)
  );
end;
$$;

revoke all on function public.gb_replace_private_opportunities(jsonb) from public,anon,authenticated;
grant execute on function public.gb_replace_private_opportunities(jsonb) to service_role;
