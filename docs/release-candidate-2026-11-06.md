# Global Broker staged release candidate — 6 November 2026

Status: **PREPARATION ONLY — NOT DEPLOYED / NOT COMMERCIALLY READY**.

Latest local publication/security evidence and remaining gates: [29 October checkpoint](release-evidence-2026-10-29.md). Baseline counts below are historical, not current acceptance.

## Deployment control
- Stage changes in this branch and review in a draft PR. Do **not** merge into `main` until the final release approval.
- Vercel team spend cap is not changed; projects may remain paused. Do not resume or trigger a paid production build without explicit user approval.
- Git-connected Vercel projects can auto-build branches. Check deployment triggers and spending before any release; a draft PR is not a deployment guarantee.
- Preserve the current production SHA/alias as rollback reference before deployment.

## Included changes (all previously passed their individual GitHub checks)
- PR #201: malformed attachment coverage counts fail closed.
- PR #204: TED Search HTTP 429 classified safely; untrusted response bodies not logged.
- PR #206: malformed cached TED extraction attempts handled safely.
- Previously merged main includes PR #203: per-format TED failure diagnostics.

## Required before marking this release candidate ready
- [ ] Combined CI, security and TED probe pass on this branch.
- [ ] Resolve TED official XML/HTML/PDF live parsing failure (#202); do not weaken notice identity, PDF magic-byte, origin or annex coverage gates.
- [ ] Real opportunity dossier and exact-spec acceptance; no fabricated buyer/supplier details or quotes.
- [ ] Confirm public/private data boundaries and mobile/customer/admin/AI Visibility handoff.
- [ ] Validate live payments and account recovery only with explicit user consent; do not reset passwords.
- [ ] Record browser smoke, production deployment readiness, Vercel spend check, rollback plan and customer acceptance.
- [ ] Request explicit user approval before the final Vercel production deployment.

## Verified baseline before combined CI
- Main: `80419503ff5798e0a5ed4126d6c8e2dd9467bb3f`.
- Last inspected real Shadow Scan: 71 opportunities; 45 TED XML attempts, 0 parsed; 0 exact-spec approvals.
- Software completion estimates previously reported: web 77%, app 72%; these are **not** verified commercial-launch scores.
