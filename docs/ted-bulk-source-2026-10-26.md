# Official daily XML package evidence

TED's documented alternative to individual notice downloads is
`https://ted.europa.eu/packages/daily/{yyyynnnnn}`.
Sources: https://ted.europa.eu/en/simap/developers-corner-for-reusers and
https://docs.ted.europa.eu/ODS/latest/reuse/download-direct.html.
The documented `/packages/notice/daily/202300001` form returned an empty 202
on this host; the explicitly documented `/packages/daily/202300001` example
returned a real gzip. No challenge, credentials or DNS guard was bypassed.

## Real observation

Official Search API metadata (`ojs-number`) identifies notice 700340-2026 as
197/2026. A standard public HTTPS download of
https://ted.europa.eu/packages/daily/202600197 returned HTTP 200,
application/gzip, 19,474,376 bytes. SHA-256:
`57caf6be58c26e5a47af9c303f4c7d6e1f1e466f5465da1f0e995f9006aca6c0`.
The complete gzip passed CRC/decompression: 198,541,312 expanded bytes and
3,803 tar members. No file was extracted by tar onto the filesystem.

| Notice | XML bytes | XML SHA-256 | Existing reader text |
|---|---:|---|---:|
| 700339-2026 | 17,671 | e479ac94f94cbdfb51e5c4ea24aabb4dd6f2e7686f3c39e0dd82047fef0bcf40 | 5,614 chars |
| 700340-2026 | 81,770 | 1f524d8d160e1b54bdcca34f09e953b8205b7c9e81fa473bec884c132c38b387 | 39,260 chars |

Both are actual eForms ContractNotice documents. Normalized embedded
NoticePublicationID and GazetteID match the requested notice and edition.
The new package selector fed both into the existing enrichment parser:
ted_xml_parsed=true; no commercial approval was granted.

## Code and boundaries

- `ted_bulk.py` bounds compressed size to 32 MiB, expanded size to 256 MiB,
  members to 12,000, target notices to 10, each XML to 2 MiB. Reject unsafe
  paths, target symlinks, duplicate/missing identities, wrong gazette IDs,
  DTD/entities, corrupt gzip and unsupported notice roots. Never tar-extract.
- Live fetch uses the existing public-DNS/redirect guards, one fixed official
  package URL and no retries/alternate hosts. An offline parser does not
  independently authenticate where a caller obtained a package.
- `enrich_opportunity(..., bulk_notice=...)` is opt-in. Invalid supplied bulk
  evidence fails without falling back to a different notice. Existing direct
  readers remain unchanged by default; no mass archive download was activated.
- `ted_bulk_probe.py` tests up to two real notices, at most two daily packages,
  independently of the still-failing direct download probe. Its success means
  notice XML acceptance only. Technical-annex acceptance remains false.

**Six new regression tests and all 658 Python tests passed locally.** The real
package was downloaded once using standard HTTPS and then parsed locally;
the default guarded downloader still needs GitHub-runner verification.

## Still open

Neither selected XML contains a direct supported technical attachment URL;
both point to procurement portals. The portal URL is not a read technical
annex. Real portal/document discovery and complete annex reading remain open.
No automatic sourcing/price/lot approval, Vercel deployment, production write,
budget change or provider call occurred. Do not close the total TED acceptance
gate from this partial but real source improvement.

## Regular scan integration candidate

The existing `enrich_payload` pipeline now supports an explicit
`bulk_enabled=True` fallback after ordinary notice reads fail. CLI enablement is
`GB_TED_BULK_FALLBACK=1`; otherwise no package fetch occurs. The staged shadow
scan workflow supplies that flag. The workflow/main production ref has not
been merged or activated.

Fallback groups only failed notices with valid explicit OJS metadata. At most
two editions and ten rows per edition are processed, serially, with exactly
one package request per edition; duplicate notice IDs share that request.
Already successful reads are untouched. Missing metadata, year mismatches,
limits, package errors and identity mismatches never become successful reads.
The whole selected package result is validated before any row is mutated.
Telemetry records attempted/failed packages, recovered/skipped notice counts.
These bounds deliberately leave excess notices open for a later scan/review.

The real-source bulk probe now exercises this same payload pipeline rather
than only calling the standalone package reader. It still explicitly reports
technical_annex_acceptance=false and does not write opportunity data.

Six additional regression tests cover disabled behavior, shared edition/ID,
hard bounds, bad metadata, package atomicity and actual summary recounting.
**All 664 Python tests passed locally.** Remote exact-head evidence is recorded
in issue #202; fixture results are not live annex acceptance.
