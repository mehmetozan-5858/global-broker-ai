-- Global Broker private-room schema used by Supabase/PostgreSQL.
-- Private schema: not exposed to anon/authenticated Data API roles.
-- Consent is append-only: revocation is a later `revoke` event, never a rewrite.

create schema if not exists private;

create table if not exists private.opportunities (
    id text primary key,
    opportunity jsonb not null,
    party_verified boolean not null default false,
    terms_signed boolean not null default false,
    access_fee_required boolean not null default false,
    access_paid boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists private.allowed_subjects (
    opportunity_id text not null references private.opportunities(id) on delete cascade,
    subject_id text not null,
    party text not null check (party in ('buyer', 'seller')),
    created_at timestamptz not null default now(),
    primary key (opportunity_id, subject_id)
);

create index if not exists allowed_subjects_party_idx
    on private.allowed_subjects (opportunity_id, subject_id, party);

create table if not exists private.consent_events (
    id bigint generated always as identity primary key,
    opportunity_id text not null references private.opportunities(id) on delete cascade,
    party text not null check (party in ('buyer', 'seller')),
    actor_id text not null,
    action text not null check (action in ('grant', 'revoke')),
    purpose text not null default 'contact_introduction'
        check (purpose = 'contact_introduction'),
    evidence_ref text not null default '',
    occurred_at timestamptz not null default now()
);

create index if not exists consent_events_lookup_idx
    on private.consent_events (opportunity_id, party, occurred_at desc, id desc);

create table if not exists private.audit_log (
    id bigint generated always as identity primary key,
    opportunity_id text references private.opportunities(id) on delete set null,
    actor_id text,
    event_type text not null,
    details jsonb not null default '{}'::jsonb,
    occurred_at timestamptz not null default now()
);

create index if not exists audit_log_opportunity_idx
    on private.audit_log (opportunity_id, occurred_at desc);

revoke all on schema private from public, anon, authenticated;
revoke all on all tables in schema private from public, anon, authenticated;
revoke all on all sequences in schema private from public, anon, authenticated;

grant usage on schema private to service_role;
grant select, insert, update, delete on all tables in schema private to service_role;
grant usage, select on all sequences in schema private to service_role;

alter table private.opportunities enable row level security;
alter table private.allowed_subjects enable row level security;
alter table private.consent_events enable row level security;
alter table private.audit_log enable row level security;
