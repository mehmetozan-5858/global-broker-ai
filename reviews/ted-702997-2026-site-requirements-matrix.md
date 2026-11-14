# TED 702997-2026 — site-specific requirements matrix (review only)

**Source of truth for this transcription:** amended 27 October 2026 technical specification, E-ZAK contract 47078; DOCX SHA-256 `ec1501d66872990cb18d0e27be2f492d8911b09d28665955ec28f757434a161e`. Source block numbers refer to the locally extracted **153 numbered non-empty paragraphs/table rows**. Evidence classification: text extracted from hash-verified official DOCX, **not** actual equipment compliance.

## New storage tank requirements by location

| Site | New tanks (count × minimum volume each) | Required min new volume | Max H (mm) | Max Ø (mm) | Roof/placement | Existing tanks to connect, when specified | Standalone delivery pump | Valve placement | Source blocks |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| Blansko | 3 × 20,000 L | 60,000 L | 5,100 | 2,450 | Flat, with overflow sensors | Not explicitly listed | **≥35 m³/h + filter** | Near mixing equipment | 57–65 |
| Boskovice | 2 × 15,000 L | 30,000 L | 4,400 | 2,450 | Conical, open-air | 2 × 10,000 L | **≥35 m³/h + filter** | Near mixing equipment | 66–73 |
| Tišnov | 2 × 25,000 L | 50,000 L | 6,500 | 2,450 | Conical, open-air, overflow sensors | Not explicitly listed | **≥35 m³/h + filter** | Near tanks | 74–82 |
| Hodonín | 2 × 20,000 L | 40,000 L | 4,800 | 2,450 | Flat, indoors | Not explicitly listed | **≥35 m³/h + filter** | Near tanks | 83–90 |
| Hustopeče | 2 × 10,000 L | 20,000 L | 3,000 | 2,350 | Flat, under shelter/space restricted | Not explicitly listed | **Not specified in site section** | Near tanks | 91–97 |
| Veselí nad Moravou | 2 × 15,000 L | 30,000 L | 4,400 | 2,400 | Conical, open-air | 1 × 5,000 L and 1 × 10,000 L | **≥35 m³/h + filter** | Near mixing equipment | 98–105 |
| Kyjov (Veselí nad Moravou site) | 2 × 10,000 L | 20,000 L | 4,550 | 2,400 | Flat, under shelter/space restricted | 1 × 10,000 L | **≥35 m³/h + filter** | Near mixing equipment | 106–113 |
| Rosice | 1 × 20,000 L | 20,000 L | 5,100 | 2,450 | Conical, open-air | 1 × 10,000 L | **≥35 m³/h + filter** | Near mixing equipment | 114–121 |
| Slavkov u Brna | 3 × 15,000 L | 45,000 L | 3,000 | 2,450 | Flat, indoors | 2 × 10,000 L | **Not specified in site section** | Near mixing equipment | 122–128 |
| Vyškov | 2 × 15,000 L | 30,000 L | 4,400 | 2,450 | Flat, indoors | 1 × 10,000 L | **≥35 m³/h + filter** | Near mixing equipment | 129–136 |
| Lechovice | 3 × 12,000 L | 36,000 L | 3,500 | 2,300 | Flat, indoors | 2 × 10,000 L | **Not specified in site section** | Near mixing equipment | 137–143 |
| Vranovská Ves | 3 × 12,000 L | 36,000 L | 3,500 | 2,300 | Flat, indoors | 2 × 10,000 L | **≥35 m³/h; filter not stated** | Near mixing equipment | 144–151 |
| **TOTAL** | **27 new tanks** | **417,000 L minimum nominal total** | — | — | — | — | **9 site sections explicitly require a standalone pump; eight say 'with filter', one does not** | — | — |

**Important:** “Not specified” means no standalone pump requirement stated *in that site subsection*, not an affirmative exclusion of pumps elsewhere in the contract. Existing tanks are **not** included in the new tank total. 417,000 L is the sum of individual minimum volumes, **not** the capacity of an independently validated engineering design.

## Shared storage-tank requirements

Source blocks 45–55: factory-new, preferably cylindrical, plastic, UV-protected, suitable for sodium chloride and calcium chloride, external fluid-level indicator, new-tank connection to mixer, plastic shutoff at outlet, optionally outdoors, flat/conical lid as site-specific. All 12 site sections explicitly require rigid **PVC D63** piping with independent filling, remixing and dispensing; some call for connections to existing tanks.

## Two new mixing devices (distinct from the 27 storage tanks)

Source blocks 1–44 specify **two** factory-new salt-solution mixing devices, allocated to:
1. **Břeclav / Hustopeče**, and
2. **Veselí nad Moravou / Kyjov**.

Each described device: integrated plastic reservoir **≥5,000 L**, two pumps with redundancy, specified pump **≥300 L/min**, corrosion-resistant PVC/plastic piping, anti-undissolved-salt labyrinth and separate dissolving reservoir, approximate 3,000 L sprayer tank fill within **10 minutes**, ≥4,500 L solution prepared in ~60 minutes, **6/4-inch** ball-valve water inlet, unit weight ≤900 kg, **400 V** cable ≥10 m, ≥10 m filling hose, density meter, flowmeter, automatic concentration control, independent mixing/dispensing. Both locations explicitly require rigid PVC D63 branch piping; buyer provides water and electric connections. Delivery includes controls/documents/training as source blocks 39–44.

**Do not conflate** the mixing device's ≥300 L/min pump specification with any site-section's separate ≥35 m³/h dispensing pump; the functions and quantities differ.

## Pending evidence and fail-closed decisions

- **Site-to-drawing engineering map:** identify whether drawings show all 27 deliverable new tanks and their actual usable capacity, exact footprint, lids, access and load-bearing base; mere design labels are not supplier compliance.
- **Existing connections:** confirm which existing tanks are present and how PVC D63, valves, isolation and sensors integrate without mistaken new-tank classification.
- **Special requirements:** verify the Blansko/Tišnov overflow sensors; the eight **explicitly filtered** standalone pumps; Vranovská Ves's standalone pump without explicit filter wording; restricted shelters at Hustopeče and Kyjov.
- **Scope/revision:** confirm TED amendment and official authoritative applicability, mandatory annex inventory, lot-wide completeness, buyer prerequisites and independent engineering approval.
- **Status:** `technical_approval=false`, `commercial_approval=false`, `supplier_acceptance=false`, `deployment_approval=false`. This is a review/control matrix, **not** a purchase list, quote, supplier qualification, product recommendation, or authorization to execute commercial acts.


## CRITICAL BLOCKER — geometric volume inconsistency detected (13 Nov 2026)

A separate read-only geometric audit of the exact-hash drawing geometry transcription found **two site-level contradictions affecting five proposed new tanks**. These are drawing-versus-requirement conflicts, not verified supplier noncompliance:

| Site (PDF page) | New tanks | Revised minimum per tank | Drawn outside Ø × height | Ideal full cylinder upper bound per tank | Shortfall to specified minimum |
| --- | ---: | ---: | --- | ---: | ---: |
| Veselí nad Moravou (p. 6) | 2 | 15,000 L | 2,400 × 3,000 mm | ~13,572 L | ~1,428 L |
| Slavkov u Brna (p. 9) | 3 | 15,000 L | 2,400 × 3,000 mm | ~13,572 L | ~1,428 L |

Formula: `maximum_geometric_envelope_L = π × (diameter_mm/2)^2 × height_mm / 1,000,000`. Using the *outside* diameter and height and assuming a completely filled perfect circular cylinder deliberately **overstates** usable liquid capacity. Thus a 13,572 L envelope cannot contain 15,000 L within those limits. Printed values rounded for review; the code compares unrounded values.

**What is not yet established:** whether drawing dimensions are correct, whether those drawings are superseded, or whether another design/model with larger height (up to the amended site's specified maximum where applicable) is intended for delivery. The drawing's `ZN 15` label is not 15,000 L physical-volume proof. Do not resolve the contradiction by assuming a model label or setting `capacity_verified=true`.

**Minimum safe resolution:** check authoritative annex revision and the buyer's technical dimension definitions, request a documented drawing clarification through an authorized procurement channel before sourcing or scoring any tank model. Obtain dimensioned, certified tank volume curves / usable fill level and site fit evidence. No contact, offer, paid action, merge, deployment or technical approval has been authorized by this note.

**Automation:** `scripts/audit_ted_tank_capacity_envelopes.py` and `tests/test_ted_tank_capacity_envelopes.py` detect and fail closed on these exact drawing discrepancies. GitHub CI test success verifies the detection logic; it **does not** turn these capacity conflicts into acceptance. `technical_approval=false`, `commercial_approval=false`.


## ESCALATED BLOCKER — amended dimensional ceilings are mutually incompatible at Slavkov

Re-examination of drawing p. 6 (Veselí nad Moravou) and p. 9 (Slavkov u Brna) reconfirmed both use **ZN 15 labels Ø 2,400 mm × 3,000 mm**, whose ideal full cylinder envelope is **13,571.68 L**, short of a 15,000 L requirement by **1,428.32 L** per tank. The drawings thus contradict the specified minimum volume for **2 + 3 tanks** if the given dimensions are their maximum outer envelopes.

**Distinguish the two situations:**

- **Veselí nad Moravou:** amended site ceiling is **Ø 2,400 mm × H 4,400 mm**. At the printed Ø 2,400 mm, even a fully utilized ideal cylindrical volume of 15,000 L requires a **minimum ideal height of ~3,316 mm** (real engineering fill height likely more). That is above its **drawn** 3,000 mm but below the site's 4,400 mm ceiling. A revised taller drawing might be geometrically possible, subject to actual tank design, usable capacity and site fit.
- **Slavkov u Brna:** amended ceiling is **Ø 2,450 mm × H 3,000 mm**, *even though the drawing uses Ø 2,400 mm*. At the site **maximum permitted dimensions**, the ideal full cylinder volume is **~14,143.06 L**, still **~856.94 L below 15,000 L**. A 15,000 L *ideal cylinder* at Ø 2,450 mm would need at least **~3,182 mm** height, which exceeds the stated 3,000 mm maximum. This is a **specification-level geometric contradiction** for a cylindrical, fully bounded tank, not merely a drawing height typo.

**Limits:** This audit applies to the dimensioned cylindrical outside envelopes stated in the specification and drawings, not to hypothetical alternative geometry/interpretations or undisclosed usable volume definitions. A human reviewer must confirm that all height/diameter dimensions, nominal volume definitions and placement constraints have that intended meaning before asserting a formal tender inconsistency.

**Next safe action:** raise a clarification request **draft only** for authorized procurement review; independently check original Czech wording and any post-27-October authority amendments, and request corrected dimensioned capacity drawing or clarification of the Slavkov volume-vs-envelope requirement and Veselí drawing height. Do **not** contact buyer or suppliers, send any question, issue an offer, or change production on this evidence alone.

This finding is recorded by `scripts/audit_ted_tank_capacity_envelopes.py` with two separate fields: `drawing_envelope_below_required_volume` and `spec_dimensional_envelope_below_required_volume`. Technical and commercial acceptance remain **false**.
