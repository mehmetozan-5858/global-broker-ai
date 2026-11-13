# TED 702997-2026 — revised tank criteria and drawing cross-check (review only)

**Evidence sources (hash-pinned, not commercial approval)**

- Original DOCX SHA-256: `7b1937a90a083cd594e3bdd82772eaa088ace4300d87676220c8d109fc7c142b`
- Amended DOCX SHA-256: `ec1501d66872990cb18d0e27be2f492d8911b09d28665955ec28f757434a161e`
- Drawings PDF SHA-256: `cab5b314b5d59fb7fad3618ec1d6398dcf8cf6f32fbce41c88a06642e09f767f`
- Source review: E-ZAK contract 47078; amended technical specification dated 27 October 2026.
- Original/amended text was compared locally with exact SHA match. Do **not** treat unchanged rows or drawing labels as an approved bill of materials.

## Verified textual amendment

| Site | Criterion | Previous technical DOCX | Amended DOCX |
| --- | --- | --- | --- |
| Lechovice | Three storage tanks, minimum volume per tank | 14,000 L | **12,000 L** |
| Lechovice | Maximum tank height | 3,300 mm | **3,500 mm** |
| Lechovice | Maximum tank diameter | 2,300 mm | **2,300 mm (unchanged)** |
| Vranovská Ves | Three storage tanks, minimum volume per tank | 14,000 L | **12,000 L** |
| Vranovská Ves | Maximum tank height | 3,300 mm | **3,500 mm** |
| Vranovská Ves | Maximum tank diameter | 2,300 mm | **2,300 mm (unchanged)** |

The amendment's text comparison reported four removed and four added lines, all pertaining to the stated minimum volume and maximum height criteria.

## Drawing pre-review, no conformity approval

- PDF p. 11, **Lechovice:** shows three tanks labelled **ZN 14**, diameter **2,300 mm**, height **3,300 mm**. Also shows two **ZN 10** tanks annotated *stávající* (existing), diameter **2,330 mm**, height **3,000 mm**. The existing tanks **must not** automatically be judged against the revised requirements for three new tanks. A *MZK 5* unit is also annotated as existing.
- PDF p. 12, **Vranovská Ves:** shows three **ZN 14** tanks, diameter **2,300 mm**, height **3,300 mm**, plus two **ZN 10** tanks labelled *stávající* (existing), diameter **2,330 mm**, height **3,000 mm**. The overall drawn area includes 13,250 mm by 5,300 mm dimension annotations and a water-meter shaft.
- On the face of these two drawings, the **three ZN 14 tank labels at both sites** are consistent with the revised diameter/height limits. The label ZN 14 is **not independently verified proof of actual capacity or deliverable equipment**, and drawings do not establish supplier compliance.
- **Unresolved:** authoritative revision applicability; technical specification requirements beyond the four changed rows; whether the three ZN 14 positions represent tender deliverables as drawn; connections and spacing; accessible service clearances; other site drawings; tender-wide completeness; engineering/supplier approval.

## Review decision

- **Evidence:** DOCX diff and the two displayed drawing pages give consistent *nominal* tank dimensions for the amended criteria.
- **Risk:** incorrectly applying new-tank maximum diameter to existing ZN 10 tanks (diameter 2,330 mm), or incorrectly treating drawing labels as supplier compliance.
- **Next safe step:** reconcile the amended DOCX's complete site requirements with all drawing details and have technical reviewer validate deliverable tank capacity, physical fit and connections.
- **Status:** REVIEW ONLY, `technical_approval=false`, `commercial_approval=false`, `deployment_approval=false`. No supplier contact, offer, price, merge or deployment authorized by this note.


## Amended DOCX equipment, piping and installation requirements (bounded extraction, 13 Nov 2026)

The following requirements are extracted from the exact-hash amended DOCX, not inferred from the drawings. Source references below are numbered blocks in the bounded private review excerpt. They are **not proof of a supplied machine's compliance**.

| Subsystem / evidence block | Requirement in amended specification | Current evidence | Missing acceptance evidence |
| --- | --- | --- | --- |
| Integrated mixing unit [5] | Integrated reservoir **at least 5,000 L** | Text requirement verified | Model-specific supplier capacity drawing and test |
| Pump redundancy / mixing pump [13–14] | **Two pumps** for rapid production and redundancy; pump **at least 300 L/min** | Text requirement verified | Pump curves, quantity and redundancy behavior |
| Piping and corrosion [6–11] | Plastic pumps, PVC distribution; independent filling, remixing and drawing off from connected tanks | Text requirement verified | Material grade, piping/isolation schematic and integration test |
| Undissolved salt [16–17] | Anti-carryover labyrinth; salt dissolving in a separate reservoir for measurement | Text requirement verified | Technical design and measurable test |
| Sprayer filling [18] | Fill approximately **3,000 L within 10 minutes** | Text requirement verified | Real loaded-flow test; rated 300 L/min alone does not establish ten-minute fill |
| Water inlet [20] | **6/4-inch** connecting neck with shutoff ball valve | Text requirement verified | Dimensional interface and plumbing compatibility |
| Fill indication and hose [23–24] | Sprayer-fill indication connection cable; at least **10 m** fill hose with shutoff ball valve and sprayer connector | Text requirement verified | Cable pinout, hose/interface documentation |
| Mixing during dispensing [28–29] | Remixes already prepared liquid; independent mixing and sprayer filling | Text requirement verified | Controls schematic and operational test |
| Overflow and isolation [62,64,72,79,81 etc.] | Overflow prevention at tanks where specified; tank valves near mixing unit or tanks, per site | Text requirement verified for named sections | Site-specific mapping and sensor test |
| Independent dispensing pump [65,73,82,90,105,113,121,136,151] | Separate pump at least **35 m³/h**, with filter **where explicitly stated**, control and location designated by buyer | Text requirement verified in specified subsections | Per-site matrix; do not assume the filtered pump applies identically at every location |
| Site preparations [33–38,152] | Buyer supplies described water/electrical hookups and preparatory work including relocating existing equipment and preparing areas | Text responsibility verified | Written interface and installation boundary agreement |

### Cross-check specific to Lechovice and Vranovská Ves

- Lechovice and Vranovská Ves each require **three new storage tanks >=12,000 L**, **maximum height 3,500 mm**, **maximum diameter 2,300 mm**, as established by the source DOCX comparison. Their *nominal* drawn ZN 14 envelopes (diameter 2,300 mm; height 3,300 mm) meet the stated dimension ceilings.
- Both drawings label ZN 10 units as *existing* (diameter 2,330 mm; height 3,000 mm). **Do not** apply new-tank dimensional ceilings to existing units or claim they are proposed deliverables.
- Lechovice's nearby-tank valves are required by [143]. Vranovská Ves additionally explicitly specifies a separate delivery pump of **at least 35 m³/h** in [151]. Its cited paragraph does **not** repeat the same filtration wording as some other site sections; avoid silently importing requirements.
- **Capacity cannot be established from the ZN 14 label alone.** Independent tank volume calculation is not decisive without reliable internal geometry, wall thickness, nozzles and allowable fill level, and drawings alone do not establish functional capacity.
- Outstanding mapping: new vs existing piping, pumps, valves and controls; electrical/water interfaces; access and maintenance clearances; site-specific clauses for remaining locations; technical site acceptance.

### Fail-closed decision

Evidence is sufficient to create a **supplier-agnostic engineering checklist**, but not to score any supplier or authorize a quote. All fields remain `technical_approval=false`, `supplier_acceptance=false`, `commercial_approval=false`, `deployment_approval=false`. Do not merge, deploy, change budget, contact suppliers or create binding offers on this evidence.
