# Technical attachment selection

Technical PDFs/DOCX/text files found late in a source page or TED XML must not
lose the three-document read budget to earlier generic portal documents.
Selection now uses deterministic filename and anchor-label hints, deduplicates
URLs, preserves source order for equal priority, and applies the existing cap
after ranking. This priority is a retrieval hint, not a technical approval.

Only existing supported formats (PDF/DOCX/TXT) are added. Explicit basename
parameters (`filename`, `file_name`, `file`, `download`) are supported for
extensionless download endpoints; nested URLs and credentials are not attachment
filename hints. HTML login/error pages are rejected as attachment text even when
the URL suggests a PDF or other supported file. Downloaded MIME/magic bytes and
existing parsers still determine whether any real text was read.

Source SSRF/redirect checks, byte/page/character limits and concurrency stay in
place. Malformed links are skipped without hiding subsequent valid documents.
Actual URL/type/attempt provenance remains in the private dossier; failed query
attachments remain unparsed instead of being presented as source pages.

Validation: nine new Python regressions cover late HTML/XML links, duplicate
labels, explicit query filenames, nested URL rejection, binary DOCX downloads,
private parser provenance, rejected login pages, script links and malformed
URLs. No supplier, price, exact-spec, buyer or commercial acceptance is inferred.
Current and future notices use this same path on every source scan.

Live source diagnosis on 21 October 2026 found 38 TED records, eight with source
text; direct TED XML/HTML/PDF attempts returned non-document/challenge pages.
This change does not bypass those source restrictions or promise a count
increase where the source publishes no usable document.
