# Customer dossier review and masked feed round trip

The authenticated opportunity API accepts the existing safe `goods_status: goods_candidate` snapshot as well as legacy raw goods reviews. An explicit non-goods raw review still rejects a row. Sector and country restrictions, user verification, active-plan checks, and the public projection remain mandatory.

The public projection retains only allowlisted customer fields through the feed-to-API round trip. Quantity, product detail, coverage counts, and canonical TED result/planning context survive without exposing buyer/contact/source-document fields. Previous-source verification dates also survive; raw notice labels are never copied into customer text.

New review metadata is restricted to source-read status enums and fixed missing-field enums. The portal displays source reading separately from full specification, buyer, and offer acceptance. Unknown-lot scopes carry no invented lot count. Both customer and admin dossiers withhold flat quantity/budget when scope review is required. No raw source excerpt or private missing-field note is added to the customer response.

Validation: 537 Python and 21 targeted JavaScript tests passed locally. Handler-level regressions cover raw and masked feeds, sector/country scope, missing session, inactive plan, conflicting goods/service status, privacy, and review metadata. The post-deploy browser test checks the exact published customer script on Chromium at 320/390/1280 px and WebKit at 390 px. All browser requests are intercepted fixtures; it creates no customer, introduction, payment, or acceptance record.

This closes a feed/display defect. It does not count as real customer acceptance or complete commercial-dossier acceptance and does not add weighted completion points.
