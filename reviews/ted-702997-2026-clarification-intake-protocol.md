# TED 702997-2026 — official clarification evidence intake (NOT acceptance)

## Purpose

A future publication concerning the **Slavkov u Brna** or **Veselí nad Moravou** tank-capacity contradictions must not silently remove the isolated-source quarantine. This document records what would be needed to evaluate a candidate clarification, not a buyer message or a tender submission.

## Steps, in order

1. **Capture official publication:** On the exact public official E-ZAK/TED host, document the publication ID, publication date, immutable source URL, file SHA-256, retrieval date, and the original undisturbed bytes in an appropriately private evidence store. No GitHub commits of raw sensitive annexes.
2. **Establish authority and scope:** Identify which official notice and which Annex 8 and technical-specification versions this publication supersedes. Match the notice, location, tank quantity and buyer-provided dimensional terms, including original Czech terms. A document's presence alone is not enough.
3. **Reconcile each of the two separate issues:**
   - Slavkov u Brna: 3 × minimum 15,000 L against maximum Ø 2,450 mm / height 3,000 mm. An ideal full cylinder at those limits is <15,000 L.
   - Veselí nad Moravou: 2 × minimum 15,000 L against drawing Ø 2,400 mm / height 3,000 mm (ideal cylinder <15,000 L), while specification allows height to 4,400 mm.
4. **Independent engineering review:** Obtain genuine usable-capacity evidence, dimensions, installation envelope and independent reviewer sign-off. Check other required equipment, connections and all 27 tank positions, not only the disputed five.
5. **Run the isolated audit and regression checks:** `scripts/audit_ted_tank_capacity_envelopes.py` and `scripts/ted_technical_acceptance_gate.py`. Do not edit historical exact-hash inputs to conceal a conflict. Create a new versioned evidence record if an official replacement changes any requirement.
6. **Separate authorization:** A complete technical review never grants supplier eligibility, price readiness, customer acceptance, payment readiness or production deployment. These require their own validated and human-approved gates.

## Candidate metadata schema (review only)

The script `scripts/ted_clarification_evidence_review.py` consumes a JSON object containing:
- `notice`: one of `702997-2026`, `746528-2026`
- `site`: exactly `Slavkov u Brna` or `Veselí nad Moravou`
- `official_url`: direct HTTPS URL with an allowed official domain
- `sha256`: 64-character lowercase SHA-256
- `official_publication_date`: YYYY-MM-DD
- `reviewer`: named independent reviewer
- `corrected_requirements`: positive integer `minimum_volume_l`, `maximum_diameter_mm`, `maximum_height_mm`

**Limitations:** The intake never fetches a URL, adjudicates the amended technical requirement or releases the quarantine. Its optional offline local-file mode calculates SHA-256 from a bounded file (maximum 12 MB) and compares it with the stated digest. Even a match verifies only local-file consistency, not official source provenance or authorized publication. Even structurally complete input produces `NEEDS_INDEPENDENT_SOURCE_REVIEW`. Any user-supplied `technical_approval` or `quarantine_release_authorized` field is ignored.

## New bounded manifest-to-file provenance consistency check (14 Nov 2026)

The optional offline function `check_official_manifest_record(candidate, manifest, private_directory)` requires a **unique** document entry matching both candidate URL and SHA-256, in a bounded E-ZAK contract 47078 manifest. The manifest must identify both notice `702997-2026` and amendment `746528-2026`, indicate its source index, and retain its explicit `revision_verified=false` and `complete_annex_set_verified=false` safeguards. A strict local annex filename, file size and recomputed file SHA-256 must also match. Malformed/missing/changed files and incorrect source identifiers fail closed.

**Trust boundary:** This verifies consistency **only** within an authentic official-fetch session. A separately supplied JSON manifest and matching bytes can both be fabricated, so this function explicitly returns `authoritative_revision_verified=false`, `source_content_verified=false`, `capacity_conflict_resolved=false`, `quarantine_release_authorized=false`. No candidate clarification was authenticated or reviewed by adding these tests.

## Current state

- Source clarification for two site discrepancies: **unverified / no resolution**.
- Internal clarification request draft: **unsent**.
- `technical_approval=false`, `commercial_approval=false`, `deployment_approval=false`.
- Scope: isolated PR #222; no merge, deployment, budget change, paid operation, supplier outreach or buyer communication.
