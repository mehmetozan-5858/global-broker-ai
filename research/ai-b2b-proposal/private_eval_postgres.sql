-- OFFLINE RESEARCH DESIGN ONLY. DO NOT EXECUTE IN PRODUCTION.
-- This migration deliberately does NOT create roles, grant schema access
-- or set a search_path. Deploy only into an isolated dedicated test DB
-- after verifying service identity and connection isolation.
BEGIN;
CREATE SCHEMA IF NOT EXISTS b2b_research_eval;
REVOKE ALL ON SCHEMA b2b_research_eval FROM PUBLIC;

CREATE TABLE IF NOT EXISTS b2b_research_eval.document_meta (
  document_id uuid PRIMARY KEY,
  source_sha256 char(64) NOT NULL,
  manifest_sha256 char(64) NOT NULL,
  assigned_reviewer text NOT NULL,
  lifecycle_state text NOT NULL CHECK (lifecycle_state IN ('RECEIVED','FROZEN','REVIEWED','QUARANTINED')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS b2b_research_eval.review (
  review_id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES b2b_research_eval.document_meta(document_id),
  reviewer_id text NOT NULL,
  outcome text NOT NULL CHECK (outcome IN ('POSITIVE','NEGATIVE','REVIEW_SCOPE','CONFLICT','UNKNOWN')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS b2b_research_eval.audit_event (
  event_id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES b2b_research_eval.document_meta(document_id),
  actor_id text NOT NULL,
  action text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE b2b_research_eval.document_meta ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b_research_eval.document_meta FORCE ROW LEVEL SECURITY;
ALTER TABLE b2b_research_eval.review ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b_research_eval.review FORCE ROW LEVEL SECURITY;
ALTER TABLE b2b_research_eval.audit_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b_research_eval.audit_event FORCE ROW LEVEL SECURITY;

-- SECURITY: No RLS policies are installed. PostgreSQL RLS remains default-deny
-- even if a test role is granted SELECT/INSERT. This avoids trusting
-- caller-controlled session settings (custom GUC values can be forged).
-- No table grants or login roles are created here. Any future grants,
-- gateway and identity checks require separate review on a test-only DB.
-- Superusers and BYPASSRLS roles are outside this protection boundary.
COMMIT;
