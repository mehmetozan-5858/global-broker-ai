# AI B2B Proposal Agent — Independent Evidence Readiness (15 Nov 2026)

**DRAFT / NO-GO.** No independent customer-authorized evaluation data has been supplied or measured in this task.

## Implemented on the research branch
- `independent_eval_gate.py`: offline measurement of false accept, missed positive, abstention and Wilson 95% upper bounds.
- `test_independent_eval_gate.py`: 17 synthetic fixture tests for contaminated labels, changed dataset hash, missing reviewer, duplicate IDs, missing evidence digest and insufficient topic/format coverage.
- Existing 90 regression cases and 20 *development-used* synthetic diagnostic cases remain separate.
- GitHub CI evidence: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43690317259

## Evaluation contract
Each independently annotated row must include:
- `id`, `actual`, `expected`, `stratum`, `evidence_hash`.
- Supported decisions: `POSITIVE`, `NEGATIVE`, `REVIEW_SCOPE`, `CONFLICT`, `UNKNOWN`.

Manifest requires:
- `origin=independent_authorized_human_gold`
- `previously_used_for_development=false`
- `frozen_before_execution=true`
- `reviewer_id`
- `sha256_canonical` matching exact canonical JSON.

**Security limitation:** All these manifest assertions are *input claims*, not independently authenticated. An adversary can forge the document, labels and manifest together. A trusted independent custodian, controlled storage and review signature are still missing.

## Interpretation and the no-go rule
- >=100 rows and coverage across TR, EN, multipage PDF, conditional language and counterparty documents are provisional *research sufficiency checks*, **not production acceptance thresholds**.
- `RESEARCH_EVIDENCE_MEASURED` only means counts are computable for the supplied data. It does not attest independent review or imply safe deployment.
- `commercial_approval=false`, `production_ready=false` are hard-coded regardless of score.
- Zero observed unsafe positives does not imply zero underlying risk. Wilson interval records uncertainty.
- Because no new human-labeled real documents were evaluated, real-world false acceptance/false rejection rates remain **unknown**.

## Next blocking work
1. Find or receive explicitly permissioned genuine example documents and independently created adjudications, outside the developer test set; do not expose private business records in a public repository.
2. Establish authenticated data-custodian/issuer binding and controlled manifest registry; do not trust a self-attested manifest.
3. Reconcile PDF rendered pages, tables and footnotes against extracted text; reject complex unverified cases.
4. Run locked blind evaluation without tuning to the labels and record full denominators and confidence intervals.
5. Independent security + business acceptance, then explicit release authorization.

No merge/deploy, no customer offer, no outbound action, no paid services.
