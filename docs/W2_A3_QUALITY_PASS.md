# W2 + A3 Quality Pass

## W2 customer portal

Customer opportunities remain physical-goods-only. The portal now:

- searches product, buyer, country and city;
- filters by country and city;
- filters by minimum source-backed core-field coverage (4/6, 5/6, 6/6);
- sorts stronger source-backed opportunities first;
- displays buyer alongside country, city, quantity, deadline and source;
- labels missing source fields explicitly instead of inventing values.

## A3 evidence refresh

A3 evidence is calculated twice in the Shadow Scan:

1. immediately after the physical-goods gate, using fields already present from official feeds;
2. again after document parsing, TED XML enrichment and specification analysis.

The second pass is important because later source-reading stages may add explicit fields. The same fail-closed rule remains: a value is only marked `source_backed` when it exists in an accepted source field. Missing values remain missing; narrative text is not promoted to a normalized city, country or quantity by inference.

## Acceptance gate

- CI must pass all brokerage regression tests.
- Customer portal JavaScript remains syntax checked by Verified Brokerage CI.
- Live payload validation still requires A2 physical-goods status and A3 evidence structures for every opportunity.
- No paid dependency is introduced by this pass.
