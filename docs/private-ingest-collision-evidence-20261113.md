# Broker private ingest: 13 Nov 2026 production read-only findings

**Release gate: BLOCKED. Do not run migrations, rekey, re-ingest or merge this PR as a production fix.**

## Evidence
- GitHub Shadow Scan run [43380128597](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43380128597):
  remote private-ingest Edge Function responded HTTP 500.
- Supabase Edge log at approx 06:40 UTC: POST to
  `/rest/v1/rpc/gb_replace_private_opportunities` returned HTTP 400.
- Database log: `duplicate_opportunity_id`. The RPC correctly refuses a
  repeated ID within a single incoming package; protection must remain.
- At 13 Nov read-only query time, **75 active private opportunity rows**,
  **1,564 archive rows** (1,364 distinct archive IDs), **0 introduction requests**.
  Six currently active opportunity IDs also occur in the archive.
- All 75 active rows have a `source` field. None has the particular
  `notice_id`/`notice-number`/`reference` JSON key set queried; source
  identity may exist under a different key. Do not infer that notice IDs are absent.

## Interpretation
The **incoming failed payload was not stored** and is not available as rows in
production. The observed error alone cannot identify which two incoming
records collided, whether they are same-source duplicate notices, distinct
source notices with the same bare ID, multiple lots or incompatible revisions.

## Smallest safe next diagnostic
1. On the next **offline or no-write local input snapshot**, run:
   `python -m src.private_snapshot_identity_gate /path/to/private-snapshot.json`.
2. Review aggregate duplicate group counts; never log or publish raw IDs,
   buyer contacts, full URLs, source documents or business descriptions.
3. Reconcile verified source namespace + publication/revision + lot scope for
   each collision, and compare active, archive and introduction references.
4. Implement ID change only with reviewed idempotent mapping, preserving
   existing references; test on isolated data and verify rollback.
5. Perform a narrowly scoped real remote ingest acceptance only after the
   snapshot has no unreviewed duplicate identities and release is approved.

No active records or archive rows were changed during this inspection.
