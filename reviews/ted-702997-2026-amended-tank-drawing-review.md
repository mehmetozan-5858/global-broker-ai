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
