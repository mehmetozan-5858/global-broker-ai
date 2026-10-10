# W2 + A3 Acceptance Gates

## W2 — Customer portal first slice
- Customer route exposes a product/country/city search experience over the live feed.
- Only `export_goods_review.status == goods_candidate` records are rendered.
- Missing quantity, city or deadline is shown as missing; the UI does not invent values.
- Source link is shown only when an HTTPS source URL exists.
- Core-field evidence coverage is visible to the user.
- JavaScript syntax is checked in CI and the script is injected only into `customer.html`.

## A3 — Source-backed core fields first slice
For every live physical-goods opportunity, these fields are assessed independently: country, city, product, quantity, deadline, buyer.

Each field records:
- source-backed value or explicit missing state,
- source field name,
- `inferred: false` for this gate.

A3 does not treat text inferred from a title as a verified country/city/quantity. The source title may back the requested product description because it is itself source content.

The live workflow fails closed if physical-goods opportunities are published without the A3 field-evidence structure. Completeness is **not** required: unknown source data must remain unknown rather than being fabricated.
