# Observed technical-document access barriers

Following the actual CallForTendersDocumentReference in official package
197/2026, notice 702439-2026 links to the 3P download portal. An anonymous GET
redirected to `/Web/Country.aspx`. A normal form-based country/language choice
led to `/Web/Information.aspx`, which presents online terms. No terms were
accepted, no account created, and no document was represented as downloaded.
Cookie/form state stayed in an ephemeral local session and is not committed.

The new source_access_barrier helper identifies these specific observed
country/terms pages and the previously observed EKR maintenance page. The
shared HTML parser rejects them before reading text or selecting attachments;
privacy/terms PDFs cannot therefore become tender-document evidence from
these pages. It performs no navigation, cookie changes or consent operations.
Normal tender pages on the same host remain parseable.

Three regression cases cover observed barriers, normal same-host documents
and unrelated text. All 667 Python tests passed locally. Real notice XML
acceptance remains verified separately; technical-annex acceptance remains
open. No production deployment or source access-control bypass occurred.
