# Global Broker release evidence — 29 October 2026

Status: prepared code and local evidence only. Not merged, deployed or commercially accepted.

Base: PR #208, `ae35bf89568973c6ae361ace4c6e1c9d19a01637`.
Inspected main: `d4b2cb6a01732b786c90f333220305e388b6b84b`.
Related: #200, #202, #205, #207, #208.

## Problem and change

Main Shadow Scan run 40877374023 failed at “Verify no restricted fields are published” with `direct contact URI published in public feed`. Commit and Pages trigger were skipped. The full failed intermediate feed was not available: its exact offending field/value is not established. The successful earlier private ingest and queue steps must not be confused with the blocked public publication.

The Shadow Scan publication step still used a recursive denylist. It now invokes the same explicit public projection module used at the other public boundaries. Unknown top-level summaries and nested private research are excluded by default. Only goods candidates are emitted; internal launch reports remain private. The independent forbidden-key/email/contact-URI verifier remains in place; only its expected mode changes to `public_allowlist_feed`.

Approved text fields can themselves contain contact data. The projector now omits an entire scalar value containing an email or `mailto:`/`tel:` marker, including a bare prefix. It does not manufacture a replacement fact or identifier. A benign-looking string containing the same marker can also be withheld conservatively; these checks are not a general personal-data detector.

Two compatibility problems exposed by switching the workflow to the shared projector are covered: numeric quantities no longer raise a scalar TypeError, and a reviewed explicit false lot-selection flag survives feed/API reprojection. True lot-selection blockers continue to take precedence.

## Local verification

- `python -m unittest discover -s tests -p 'test_*.py'`: **678 tests passed**.
- `node --test tests/*.test.cjs`: **89 tests passed**.
- `git diff --check`: passed.
- Baseline reproduction confirmed that `tel:` survived in `product_detail` and numeric quantity raised TypeError; the changed projector rejects/preserves these respectively.
- The real workflow build and verifier commands were executed on isolated synthetic input. Unknown private summaries/research and private document text did not reach output; known document-coverage blockers did. Injecting `tel:` into the generated output still failed the independent gate.
- Local production-entrypoint HTTP tests returned 200 for public/customer/admin-shell/contact/handoff routes and 401 without credentials for `/api/private_room`, `/api/admin_opportunities`, `/api/opportunities` and `/data/latest-opportunities.json`. A 200 admin shell does not grant admin data access. Repository path traversal stayed 403.
- Existing company handoff tests passed: four approved profile fields, fixed destinations, no token/contact transfer, invalid payload rejection. This is contract evidence, not a live two-application browser round trip.
- Added four-case stale-approval check: truncation, skipped annex, failed annex and revision ambiguity block dossier/supplier/workflow. Replacing extraction metadata with complete coverage allows technical analysis again but does not restore the previous dossier/supplier/workflow approval.

## Remaining release gates

| Gate | Evidence now | Still required |
| --- | --- | --- |
| Public publication | Local workflow build/verifier and adversarial fixtures pass | Exact-candidate remote CI and approved operational acceptance; no production scan was rerun |
| Source and annex completeness | Earlier #208 sample read remains 3 of 10 observed links; no new acceptance | Complete inventory, applicable version and human exact-spec review; preserve sourcing denial |
| Fresh source access | One bounded local annex probe failed `non_public_or_unresolvable_url` before source reading | Runner with permitted source access; this failure proves neither a remote TED outage nor a successful document read |
| UI widths and bilingual warnings | Existing Node/Python regressions pass | Real browser evidence at 320/390/1280 and TR/EN; local browser installation failed because the downloaded archive was invalid |
| AI Visibility handoff | Broker-side contract regressions pass | Same-version, two-application browser acceptance with synthetic data and no external writes |
| CI and cost | Existing CI is one Ubuntu job with Python/JS tests and read-only permission | Check actual Actions allowance/account usage externally; no free-cost guarantee inferred |
| Manifest and rollback | Base/main SHAs and exact change available for review | Final candidate SHA and production rollback alias/SHA at the separately approved release window |
| Commercial and Vercel | No new approval or environment evidence | Same-opportunity supplier quotation, customer acceptance, payment/refund validation, current budget/pause/alias checks and explicit launch approval |

No source gates or download limits were relaxed. No full Shadow Scan, private ingest, introduction processing, payment, customer write or messaging was initiated. No branch/reference update, merge, deployment, Resume, budget or live configuration change is part of this evidence checkpoint. GitHub object storage alone must not be treated as remote CI completion.
