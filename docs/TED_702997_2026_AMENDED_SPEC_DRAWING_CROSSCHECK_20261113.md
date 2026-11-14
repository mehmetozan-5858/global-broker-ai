# TED 702997-2026 — amended technical specification / drawings cross-check (review only)

Date: 2026-11-13. Scope: official E-ZAK procurement 47078, only hash-pinned existing sources.
No source, supplier, pricing, quote, deployment, or commercial acceptance change.

## Evidence
- GitHub workflow run 43454796295: original DOCX SHA-256 `7b1937a90a083cd594e3bdd82772eaa088ace4300d87676220c8d109fc7c142b` compared with amended 27 October DOCX SHA-256 `ec1501d66872990cb18d0e27be2f492d8911b09d28665955ec28f757434a161e`.
- Paragraph/table-row text comparison: 153 lines each, 16 unified diff lines. Diff is an evidence aid, **not** a full OOXML structural or revision review.
- Drawing PDF SHA-256 `cab5b314b5d59fb7fad3618ec1d6398dcf8cf6f32fbce41c88a06642e09f767f`; 12 pages rendered from this exact file. Pages 11 and 12 show the two amended sites.

## Material text changes found
| Site | Original DOCX | Amended DOCX (27 Oct) | Unchanged maximum diameter |
|---|---|---|---|
| Lechovice | 3 tanks, minimum 14,000 L each; maximum height 3,300 mm | 3 tanks, minimum 12,000 L each; maximum height 3,500 mm | 2,300 mm |
| Vranovská Ves | 3 tanks, minimum 14,000 L each; maximum height 3,300 mm | 3 tanks, minimum 12,000 L each; maximum height 3,500 mm | 2,300 mm |

## Drawing visual observations (NOT procurement acceptance)
- Page 11 (Lechovice) shows three **ZN 14** tank symbols at **Ø 2,300 mm** and **height 3,300 mm**; two **ZN 10** tanks marked *stávající* (existing) at Ø 2,330 mm and height 3,000 mm. Existing tanks must not be counted as the proposed three tanks without further evidence.
- Page 12 (Vranovská Ves) shows three **ZN 14** tank symbols at **Ø 2,300 mm** and **height 3,300 mm**; two **ZN 10** tanks marked *stávající* (existing) at Ø 2,330 mm and height 3,000 mm.
- On the drawing labels, the three ZN 14 symbols at each site appear within the amended **diameter <= 2,300 mm** and **height <= 3,500 mm** dimensional bounds.
- **Important:** "ZN 14" is a drawing label, not an independently verified usable-volume certificate. Neither exact usable capacity >= 12,000 L, installation clearances, fittings, structural/safety suitability, nor compliance with all tender terms is proven by the drawing alone.

## Remaining mandatory gates — BLOCKED
1. Confirm amendment 746528-2026 and the current authoritative document revision, including any later changes.
2. Reconcile document/annex and lot completeness with the contracting authority's final list. Ten hash-matched PDFs/Office files do **not** prove mandatory set completeness.
3. Independently establish effective capacity, connections, clearances, safety requirements, and actual product/vendor evidence for each of the two sites.
4. Review all remaining drawings against all sections of the amended specification; secure independent human review.
5. Do not conflate source-file checks, restricted XLSX formula math checks, or rendered drawings with commercial acceptance.

**Decision:** `technical_approval=false`; `supplier_sourcing_ready=false`; `commercial_approval=false`.
