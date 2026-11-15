# AI B2B Proposal Agent — pinned text ingestion (offline)

**NO-GO / Research-only.** CI evidence: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43626630900

## Verified scope
- Python standard library, bounded UTF-8 `bytes`, max 1 MiB and 10,000 physical lines.
- Source ID, expected raw SHA-256, company and region are required from an **externally maintained manifest**.
- The raw hash is checked before line extraction. Stable physical line IDs `L1`, `L2`, etc. are emitted, preserving blank-line positions.
- The derived source snapshot then passes exact-line comparison through `verify_source_bound_v9`.
- Missing/altered bytes, unsupported encodings and control characters fail closed.
- PDF, scans, OCR, DOCX and remote URL retrieval are **not implemented**. PDF magic is rejected. There is no production integration or document authenticity check.

## Critical limitation
Anyone who can modify both document bytes and expected manifest digest can fabricate an internally consistent snapshot. Independent provenance, allowed custodians, a pinned authoritative registry, version history, legal entity verification, certificate authority checks and external source validation remain required. The prototype must never turn `source_integrity_verified` into an assertion of truth or a commercial approval.

## Remaining acceptance gates
1. Immutable/persisted document storage and independent manifest administration.
2. Safe PDF parser with explicit pages and extracted text-to-page reconciliation (reject image-only or unreadable PDFs).
3. Real customer-authorized holdout dataset with human-labeled expected decisions.
4. False acceptance and false rejection measurements under adversarial examples.
5. Review API contract, access isolation, security controls and permissioned acceptance.

**No merge, no deploy, no automatic offer.**
