# World Bank official notice body reader

The document pipeline reads the public World Bank procurement API for each valid current `WORLD_BANK` notice ID. It requests only `id,notice_text` using that OP identifier and requires exactly one matching ID before accepting text. It checks the final HTTPS API origin and path, rejects missing, short, oversized and ambiguous bodies, and uses the existing network limits and public-address restrictions.

Visible HTML is converted to text with paragraph boundaries. The private extraction records the API address, matching notice ID, format, read time and text size. The public projection excludes document text, API addresses and private contact details. This is an official notice body, not proof that every specification attachment has been obtained or that the buyer/supplier has passed due diligence.

A successful API read replaces the JavaScript notice shell as the source page. An API failure falls back to a fresh read of the canonical notice page. No prior notice text is substituted. Each scheduled scan repeats the read. The existing metadata search intentionally continues to exclude raw notice HTML and personal contact fields.

Notices mentioning lots retain the body for private review but set `source_lot_selection_required`. This blocks automatic flat commercial-term promotion, supplier specification readiness, and complete-dossier status until the procurement scope is resolved. Detection is conservative and may require manual review even for a single lot. No automatic lot-selection UI or guessed aggregation is introduced.

Only existing explicit-label extraction can add commercial terms. No quantities, budgets, supplier prices, commercial approvals, or weighted completion points are invented.

Validation: 527 Python tests passed locally, including exact-ID matching, duplicate/mismatched IDs, invalid ID, unexpected API redirect, oversized body, API failure fallback, public projection privacy, clean commercial fields and lot-scope blocking.
