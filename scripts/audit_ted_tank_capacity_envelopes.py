"""Review-only, conservative cylinder-envelope check of transcribed TED tank drawings.

The figure is an upper bound for a tank whose *entire volume* fits within a
circular cylinder of the stated outside diameter and overall height.
It is NOT actual usable volume, nominal supplier capacity, or compliance.
No network, external dependencies, offers, or approval writes.
"""
import json
import math
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "reviews" / "ted-702997-2026-drawing-geometry-matrix.json"


def audit(data):
    if data.get("technical_approval") is not False or data.get("commercial_approval") is not False:
        raise ValueError("Evidence matrix must keep acceptance closed")
    rows = data["rows"]
    if len(rows) != 12 or sum(r["count"] for r in rows) != 27:
        raise ValueError("Expected the bounded 12-site, 27-tank review")
    results = []
    for item in rows:
        if item.get("capacity_verified") is not False:
            raise ValueError("Drawing labels cannot establish usable capacity")
        d = item["drawing_diameter_mm"]
        h = item["drawing_height_mm"]
        target = item["min_volume_l"]
        count = item["count"]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0 for v in (d, h, target, count)):
            raise ValueError("Invalid dimensional input")
        upper_l = math.pi * d * d * h / 4 / 1_000_000
        # Always use a strict upper-bound comparison, not rounded display numbers.
        impossible = upper_l < target
        results.append({
            "site": item["site"],
            "drawing_page": item["page"],
            "new_tank_count": count,
            "required_each_l": target,
            "outer_cylinder_upper_bound_each_l": round(upper_l),
            "deficit_each_l_if_impossible": math.ceil(target - upper_l) if impossible else 0,
            "drawing_envelope_below_required_volume": impossible,
            "usable_volume_verified": False,
            "technical_approval": False,
        })
    return {
        "method": "outer_cylindrical_geometric_envelope_only",
        "scope": "manual_drawing_dimensions_review_not_supplier_geometry",
        "rows": results,
        "sites_with_impossible_envelope": sum(r["drawing_envelope_below_required_volume"] for r in results),
        "tanks_in_impossible_envelopes": sum(r["new_tank_count"] for r in results if r["drawing_envelope_below_required_volume"]),
        "independent_capacity_validation": False,
        "technical_approval": False,
        "commercial_approval": False,
    }


if __name__ == "__main__":
    result = audit(json.loads(SOURCE.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["tanks_in_impossible_envelopes"]:
        raise SystemExit(2)  # Fail closed: manual drawing/spec discrepancy
