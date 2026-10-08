-- Global Broker private-room durable storage schema (PostgreSQL compatible)
-- Designed for append-only consent/audit events and explicit access gates.

create table if not exists private_room_opportunities (
    opportunity_id text primary key,
    opportunity_json jsonb not null,
    party_verified boolean not null default false,
    terms_signed boolean not null default false,
    access_fee_required boolean not null default false,
    access_paid boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists private_room_allowed_subjects (
    opportunity_id text not null references private_room_opportunities(opportunity_id) on delete cascade,
    subject_id text not null,
    created_at timestamptz not null default now(),
    primary key (opportunity_id, subject_id)
);

create table if not exists private_room_consent_events (
    event_id bigserial primary key,
    opportunity_id text not null references private_room_opportunities(opportunity_id) on delete cascade,
    party text not null check (party in ('buyer', 'seller')),
    actor_id text not null,
    action text not null check (action in ('grant', 'revoke')),
    purpose text not null default 'contact_introduction',
    evidence_ref text not null default '',
    event_at timestamptz not null,
    created_at timestamptz not null default now()
);

create index if not exists private_room_consent_latest_idx
    on private_room_consent_events (opportunity_id, party, event_at desc, event_id desc);

create table if not exists private_room_audit_log (
    audit_id bigserial primary key,
    opportunity_id text,
    subject_id text,
    action text not null,
    decision text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- Never update or delete consent events in normal application flow.
-- Revocation is represented by a later append-only 'revoke' event.
