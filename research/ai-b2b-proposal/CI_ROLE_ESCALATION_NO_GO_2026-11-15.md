# AI B2B Proposal Agent — Privilege Escalation CI Evidence

**15 November 2026 — DRAFT / NO-GO; isolated R&D only**

## Actual results
- CI run: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43692176516
- Python regression: **156 / 156** tests passed.
- Ephemeral PostgreSQL 16: **32 / 32** integration tests passed (8 default-deny + 24 reviewer role scenarios).
- Development-used synthetic decision examples remain 20/20; NOT an untouched independent evaluation.

## New cases
Attempts to switch to a peer reviewer role or administrator role, change row-level security, create an overly permissive policy, obtain edit/grant rights, impersonate another reviewer by spoofing caller-defined session settings, and read or delete another reviewer's rows were checked in a throwaway PostgreSQL CI container.

**PostgreSQL GRANT nuance:** unauthorized GRANT may emit a WARNING and return without an exception. The integration test now checks actual resulting privileges using `has_table_privilege`, rather than requiring a specific exception. An earlier CI run failed because the initial test assumed every unauthorized GRANT must raise; this was a test assertion issue, not evidence that additional database permissions were obtained.

## Critical limits
1. Neon `list_projects` remains unavailable with `Tool list_projects not found`; no cloud DB, branch, role or real login was inspected.
2. The working reviewer read policy is **CI fixture only**; repository draft schema remains default-deny and cannot operate an actual review flow.
3. PostgreSQL login credentials here are artificial disposable CI credentials, not a production auth gateway or customer sign-in integration.
4. No real data, independently authenticated custodian, human-labeled holdout or external issuer/certificate verification has been established.
5. Successful tests are evidence for tested cases only, not production security certification.

**No PR merge, deploy, paid resource, Neon mutation, real customer data, commercial offer or outgoing communication.**
