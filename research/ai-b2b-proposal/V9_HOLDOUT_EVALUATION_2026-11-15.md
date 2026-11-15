# AI B2B Proposal Agent — v9 synthetic evaluation, 15 Nov 2026

**Status: DRAFT / NO-GO. No genuine customer validation, independent holdout or commercial acceptance.**

## Reproducible evaluation
- Dataset: `evaluation_holdout_v9.py`, **20 manually authored synthetic** scenarios (English support, uptime guarantees, ISO 27001; conditions, temporal/geographical restrictions and other entities).
- Runner: `evaluate_holdout_v9.py` counts exact matches, unsafe positive verdicts and rejected positives separately. CI step exits nonzero if any unsafe positive is detected.
- Prior 90 existing offline regression cases are a separate developer test set.

## Initial measured evidence — before remediation
- Run: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43689076348
- 12 / 20 decisions matched authored expectation.
- **8 unsafe positive verdicts**, **0 positive false rejects** on this small set.
- The unsafe positives occurred in contract exceptions, limited plans/regions, conditional statements, other subsidiary and future dates. The CI **failed**, as intended.

## After code correction
- Run: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/43689162008
- Existing 90 regression cases passed.
- Same 20 development diagnostic cases: **20/20 exact; 0 unsafe positives; 0 false rejects**.
- **Important: This is no longer a genuinely untouched holdout.** These cases exposed the defects and informed the changes, so the post-fix score cannot be presented as independent generalization evidence. The evaluation file is retained for regression protection only.
- Decision rule now conservatively requires human review for restricted or conditional claims. It is an incomplete language heuristic and can still produce false positives on unseen expressions.

## Strict remaining acceptance blockers
1. **Independent, newly assembled and untouched** Turkish/English evaluation set of authorized documents with human gold labels, including diverse multipage PDF tables, footnotes and corporate identifiers.
2. Separate false-acceptance and false-rejection rates, confidence intervals and scope/coverage on that untouched set; thresholds must be defined before testing.
3. Independently sourced document manifest, company/issuer identity and certificate verification.
4. Visual-to-extracted PDF reconciliation and protection against adversarial malicious PDFs.
5. Security review and explicit commercial acceptance. The prototype cannot issue real quotes, authorizations, payments or outbound messages.

No merge or deploy. PR #224 remains draft.
