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


## 5 November final cross-product acceptance checkpoint (review-only)

This is a **read-only evidence reconciliation**, not a new release approval. Latest verified draft heads:

| Surface | Exact draft head | Proven | NOT proven |
| --- | --- | --- | --- |
| Global Broker PR #218 | `f293e05b482381da6ec4be29492ca45f9c787d0d` | 13 offline pure TED notice-gate regressions passed on the fetched code subset; source/history separation staged | No exact-head GitHub Actions CI run (nested PR base); official complete technical annex; multi-lot review; 13 XLSX formulas; matching actual supplier quote; live production |
| AI Visibility PR #221 | `5d35c8fccae6206abfc1a97b8904e3735cdef6c6` | GitHub CI run `42031876918` and Web & Mobile Production Smoke run `42031877119` both completed SUCCESS, including apex/www Paddle readiness correction | ZERA production attempt result; signed Paddle webhook acceptance; actual customer checkout and settlement; deploy of this exact head |
| Future Signal PR #44 | `b007e7ac1d82ccf88fd6b24a803ffe7324e9a4f4` | private video job status fail-closed review code and offline subset tests; malformed identity regression present | No exact-head CI run (nested PR base); actual H.264/AAC MP4 with Turkish narration; physical iPhone playback; publish approval |

### External deployment and payment evidence
- Vercel `ai-visibility`: most recent deploy is **BLOCKED**, older production deploy `ffa9ab263a45c29726f396c8944f375057e365a9` is READY. The reviewed PR head is **not** the deployed production commit.
- Vercel `global-broker`: latest production attempt **BLOCKED** at unrelated commit `d16a261bb1c08bbf7367e32fbfb3bab20d7e83dd`. Do not infer user-facing readiness from old aliases.
- Vercel `future-signal-studio`: latest READY preview is older SHA `c16336e361565368c9fcfb72f9d72824a1f6825b`, not PR #44.
- Paddle Live has an approved apex checkout domain and configured default `https://www.aivisibilityworks.com/paddle-checkout`; code creates inline checkout item/product rather than relying on saved catalog products. Paddle Live transaction observed in status **ready**, not **completed**; no verified completed merchant settlement, active subscription or delivered signed webhook for this app. Never mark payment green based only on generic Paddle event counters.
- Admin-only ZERA GET requires verified `ai_admin` session and production database; no such authenticated attempt record was read. Do not POST or replay provider calls in order to obtain a status.
- Public checkout fetch via current external retrieval tool was inconclusive; do not equate tool retrieval failure with website downtime.

### Hard release decision
**GO** for preserving reviewed draft changes and independently repeating offline/no-cost tests only.
**NO-GO** for production merge/deploy, unpause, Vercel spend-limit changes, paid provider calls, real checkout, or publication without the owner's explicit per-action approval.

### Minimal acceptance sequence
1. With existing authorized production admin session, invoke only authenticated ZERA **GET** and inspect scrubbed attempt status; resolve DB mismatch without touching other tenants. Do not invoke POST.
2. Verify Paddle checkout URL/browser load, account live readiness, exact customer-linked transaction and signed webhook delivery **without a new charge** where evidence already exists; to run a genuine checkout, first obtain separate explicit approval.
3. On a cost-free runner, perform complete exact-head Global Broker Python/JavaScript/security tests and source/lot/annex/XLSX human audit; refuse source-truncated or missing attachments and fabricated quotes.
4. On a cost-free runner, perform complete Future Signal build and generate one real H.264/AAC 9:16 draft; verify on physical iPhone, no publication.
5. Only when blockers are evidenced and operational spending is explicitly approved, confirm production aliases/rollback reference and authorize individual deploys. Record exact deployed SHA and live end-to-end customer acceptance.

**Result: Software staged; commercial release NOT ACCEPTED as of 2026-11-05.**
