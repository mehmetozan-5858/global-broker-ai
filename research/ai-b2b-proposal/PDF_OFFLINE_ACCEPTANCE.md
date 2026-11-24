# AI B2B Proposal Agent — Offline PDF Page Evidence Acceptance

**Status: DRAFT / NO-GO** (15 November 2026).

## Actual verification evidence
- GitHub Actions run: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43688724249
- v9 baseline + source-integrity + pinned text + pinned PDF: **90 synthetic tests** passing.
- New `proposal_pdf_ingest.py` and `test_proposal_pdf_ingest.py` implement a bounded, text-only PDF pilot, not a document authenticity service.

## Input constraints
- PDF bytes, max 2 MiB, 1–20 pages.
- Externally pinned SHA-256 of original raw bytes; required source ID/company/region.
- `pypdf==6.1.1` runs offline; no HTTP fetching, no OCR, no paid APIs.
- Fail closed for malformed, encrypted, textless, scanned/image-containing pages, and inconsistent hash/metadata.
- Outputs source IDs and page-line labels `P1-L1`, `P2-L1` etc., with exact extracted line text.
- Preserves extracted text but DOES NOT verify page visual geometry, signatures, actual issuer, claims or certification status. The labels are generated from parser output, **not** guaranteed to correspond to visually printed lines in the PDF.

## What success does NOT prove
- Independently sourced, trustworthy issuer/custodian.
- Accurate extraction of tables, footnotes, headers, columns or visual relationships.
- Cryptographic PDF signing or legal attestation.
- External registry/certificate status.
- Human-verified false-acceptance / false-rejection rates on real authorized documents.

## Remaining blockers
1. Independent approved manifest/issuer registry and immutable document custody.
2. PDF page visual reconciliation and trusted handling of image-only or mixed-content pages.
3. Genuine permissioned holdout dataset with human gold labels (including complex multipage/tables).
4. Measurements of false positives, false negatives and uncontrolled parser edge cases.
5. Security review for malicious PDF input, separate sandbox, restricted filesystem and no egress.
6. Commercial acceptance and production release review.

**Do not merge, deploy, submit quotes, send messages, process payments or automatically approve documents.**
