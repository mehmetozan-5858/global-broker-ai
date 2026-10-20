# Scope-preserving World Bank quantity tables

The official notice-body reader now recognizes one explicit five-column layout: lot, product description, quantity, physical unit and destination. This is a deliberately bounded parser, not a general inference engine.

It requires a unique header, consecutive explicit lot identities, positive quantities with valid digit grouping, recognized units, and non-contact destination cells. Duplicate product rows within a lot, malformed numbers, incomplete rows, unknown units, duplicate headers, oversized input and mixed/ambiguous layouts reject the entire table. No prefix of a corrupted table is accepted.

Facts remain private source line items with their lot, product, quantity, unit, destination and exact notice API provenance. They never become an aggregate quantity, supplier quote, price, full-spec approval, automatic lot selection or verified buyer. Existing scope blockers remain active in source-term extraction, dossier completeness and specification checks; the shared financial UI also blocks World Bank scope reviews.

Authorized admin dossiers show individual source rows. Customer projection exposes only row and lot counts, preserves them through the API projection, and hides raw source rows, destinations and URLs. Customer cards distinguish row extraction from scope selection.

The initial live candidate has four geographic lots and twelve source rows. The parser uses the layout rather than a hardcoded notice identity or quantities, so new notices with the same validated layout are supported in future scans. Other source layouts remain pending review.

Validation is performed by GitHub CI and production scan/browser checks because the interactive execution environment is unavailable. Ten Python regressions cover clean tables, corrupt layouts, provenance, privacy and scope blocking; two JavaScript regressions cover blocked readiness and escaped admin rendering. The existing deployed customer browser suite also checks safe row counts. Tests do not create commercial evidence or real customer acceptance. No delivery points are awarded merely for writing this parser.
