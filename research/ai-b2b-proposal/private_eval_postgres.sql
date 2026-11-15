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

-- These policies are DOCUMENTATION-ONLY: custom GUCs are caller-controlled
-- if users can issue arbitrary SQL. An authenticated, narrowly scoped
-- service gateway MUST inject verified identity; do not grant direct SQL.
-- No grants are issued here: access remains denied unless separately approved.
CREATE POLICY document_owner_read ON b2b_research_eval.document_meta
  FOR SELECT USING (
    current_setting('b2b_eval.actor_role', true) = 'custodian'
    OR (current_setting('b2b_eval.actor_role', true) = 'reviewer'
        AND assigned_reviewer = current_setting('b2b_eval.actor_id', true))
  );
CREATE POLICY review_assigned_read ON b2b_research_eval.review
  FOR SELECT USING (
    reviewer_id = current_setting('b2b_eval.actor_id', true)
    AND current_setting('b2b_eval.actor_role', true) = 'reviewer'
  );
CREATE POLICY audit_custodian_read ON b2b_research_eval.audit_event
  FOR SELECT USING (
    current_setting('b2b_eval.actor_role', true) = 'custodian'
  );
-- No INSERT/UPDATE/DELETE policy: default-deny. Thus even an authenticated
-- user cannot write before a separate controlled procedure is reviewed.
COMMIT;
