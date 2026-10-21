# Partial technical comparison worker

The source worker now extracts clause records while each successfully parsed
attachment is still associated with its own URL. The first supported layout is
an explicit two-column Italian urban-CNG-bus requirement table. It extracts only
the first explicit lot column: length range, total passengers, class, emission
and fuel. Header/row ambiguity, duplicate tables, unsupported units and uncertain
values remain unstructured. The other lot is never inferred or selected.

This is deliberately partial coverage: every other specification, evaluation,
commercial and eligibility condition still needs review. It contains no notice
ID, buyer name or fixed 7–8 m/27-passenger requirement binding; values are read
from recognized source rows. Other formats/product families receive a pending
structure-review task rather than fabricated clauses.

`technical_matcher` runs automatically after the existing remaining pipeline on
every Shadow Scan. It replays clauses against the current retained source text
and parsed attachment provenance. The source record and manufacturer observations
must be fresh within one hour for this same-run comparison. Prior scopes or
caller-edited clause values are not reused after a failed/changed source refresh.

Only when supported scopes exist, refresh three approved official model pages
once per scan, concurrently: Rošero FCLEI, Rošero FCLLI and INDCAR Mobi City CNG
family. This is a bounded registry, not autonomous worldwide supplier discovery.
Only the two Rošero model tables currently yield exact millimetre dimensions.
Optional CNG or family availability requires offered-configuration confirmation;
passenger count, emission and class remain unknown without corresponding model
proof. A numeric length must agree with its mm quote; boolean/NaN/infinity,
changed model paths, wrong variants, conflicting values and failed/stale catalogues
cannot produce supported evidence. INDCAR family evidence cannot become a
specific model/configuration match.

Per-clause results distinguish source-supported values, conflicts, configuration
confirmation, missing evidence and unavailable catalogues. The existing admin
tender dossier renders supported scope/model results and safe source links, with
explicit partial-coverage and lot-review warnings. Unknown formats show no model
result. Manufacturer and clause values are escaped; unsafe/credentialed links
are omitted. Private quotes, URLs and comparison fields remain excluded by the
public allowlist projection.

This worker never changes supplier verification, exact-spec approval, financial
eligibility, source lot-selection flags, quotations, payment or launch gates.
All comparisons require human review and carry zero exact-spec approvals even
when a limited clause is source-supported. No messages, catalogue forms or bids
are sent. No new LLM calls or paid service were added.

Validation: 590 Python and 88 JavaScript tests locally, including ten extraction,
source replay, scope/unit/model isolation, freshness, failed catalog, privacy and
read-once tests plus three rendering/link-escaping tests. A captured real Livorno
PDF yielded one explicit lot scope and five clauses. Local catalogue network
resolution was unavailable and correctly produced zero comparisons with current
catalogue evidence; post-merge production scan is the separate live verification.

## Repeated lot/goods table support

The source worker also handles a second explicit layout: repeated reference/LOT
headers followed by Description of Goods / Unit / Amount rows. For fire truck
products explicitly stating CAPACITY OF AT LEAST ... LITERS, it extracts only
the minimum tank capacity. Each product has a separate scope even within the
same lot. Product quantities are retained separately and never added together.
Dimensions mentioned in other product names are not interpreted as truck length.

Sequential lots, a consistent reference, complete rows, Number units, positive
integer quantities and a numbered paragraph ending the table are required.
Ambiguous, duplicated, damaged or truncated tables remain unstructured. No buyer,
notice ID, city or capacity is hardcoded. The same parser runs for existing and
future notices during the scheduled source scan. Exact-ID official World Bank
API text now participates in source-backed requirement extraction and same-run
replay, with the same freshness and failed-refresh protections as attachments.

Catalogues are isolated by product family. A fire truck requirement cannot be
compared with the current bus registry. Until a suitable official manufacturer
registry exists, its status is manufacturer_research_required with zero model
comparisons. The admin dossier displays the minimum requirement and official
notice link, explicitly stating that manufacturer evidence is missing. This
expands requirement extraction, not verified supplier coverage or acceptance.

A read-only replay against current OP00473154 extracted three product scopes:
lot 3 has minimum 4,000 L / 7 units and minimum 3,000 L / 3 units; lot 4 has
minimum 5,000 L / 8 units. No quantities or lots were combined.
