from __future__ import annotations

from collections import Counter
from typing import Any

from .opportunity_identity import stable_opportunity_id


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return " ".join(filter(None, (_text(v) for v in value.values())))
    if isinstance(value, list):
        return " ".join(filter(None, (_text(v) for v in value)))
    return str(value).strip()


def _product(item: dict[str, Any]) -> str:
    field = item.get("field_evidence") if isinstance(item.get("field_evidence"), dict) else {}
    product = field.get("product") if isinstance(field.get("product"), dict) else {}
    return _text(product.get("value") or item.get("product_name") or item.get("title_tr") or item.get("title_original"))


def _destination(item: dict[str, Any]) -> str:
    return _text(
        item.get("delivery_location")
        or item.get("buyer_city")
        or item.get("city")
        or ((item.get("field_evidence") or {}).get("country") or {}).get("value")
        or item.get("country")
    )


def _verified_suppliers(item: dict[str, Any]) -> list[dict[str, Any]]:
    research = item.get("supplier_research") if isinstance(item.get("supplier_research"), dict) else {}
    candidates = research.get("candidate_suppliers") if isinstance(research.get("candidate_suppliers"), list) else []
    return [c for c in candidates if isinstance(c, dict) and c.get("verified") is True]


def _task(opportunity_id: Any, agent: str, reason: str, query: str | None, criteria: list[str], priority: int) -> dict[str, Any]:
    return {
        "opportunity_id": opportunity_id,
        "assigned_agent": agent,
        "reason": reason,
        "research_query": query,
        "priority": priority,
        "status": "research_required",
        "acceptance_criteria": criteria,
        "source_backed_only": True,
        "human_approval_required": True,
        "external_outreach_enabled": False,
    }


def build(payload: dict[str, Any]) -> dict[str, Any]:
    """Create fail-closed research tasks for unresolved commercial blockers.

    This module does not invent prices, freight, quantities or terms. It only
    turns missing commercial facts into source-backed research instructions.
    """
    rows = [row for row in (payload.get("opportunities") or []) if isinstance(row, dict)]
    tasks: list[dict[str, Any]] = []
    agents: Counter[str] = Counter()

    for row in rows:
        feasibility = row.get("commercial_feasibility") if isinstance(row.get("commercial_feasibility"), dict) else {}
        if feasibility.get("calculation_ready") is True:
            continue

        blockers = set(feasibility.get("blockers") or [])
        missing = set(feasibility.get("missing_inputs") or [])
        unresolved = blockers | missing
        if not unresolved:
            continue

        oid = row.get("id") or row.get("opportunity_id") or row.get("publication-number") or row.get("notice_id") or stable_opportunity_id(row)
        product = _product(row)
        destination = _destination(row)
        suppliers = _verified_suppliers(row)
        supplier_names = [str(s.get("name")) for s in suppliers if s.get("name")]
        supplier_hint = supplier_names[0] if supplier_names else ""

        if "unit_price" in unresolved or "verified_supplier_quote" in unresolved:
            query = None
            if product:
                query = f'"{product}" price quote manufacturer'
                if supplier_hint:
                    query = f'"{supplier_hint}" "{product}" price quote'
            tasks.append(_task(
                oid,
                "Price Agent",
                "verified_unit_price_required",
                query,
                [
                    "verified supplier identity already established or re-verified",
                    "unit price captured exactly from a source-backed quote or official price source",
                    "currency captured explicitly",
                    "HTTPS quote/source URL stored",
                    "no inferred or estimated price accepted",
                ],
                100 if suppliers else 70,
            ))
            agents["Price Agent"] += 1

        if "freight" in unresolved or "destination" in unresolved:
            query = None
            if product and destination:
                query = f'"{product}" freight quote to "{destination}"'
            elif destination:
                query = f'freight quote to "{destination}"'
            tasks.append(_task(
                oid,
                "Logistics Agent",
                "verified_freight_or_destination_required",
                query,
                [
                    "origin and destination captured explicitly",
                    "freight amount and currency captured from carrier/forwarder evidence",
                    "service scope and transport mode recorded when present",
                    "HTTPS source/quote URL stored",
                    "no estimated freight accepted",
                ],
                95 if suppliers else 65,
            ))
            agents["Logistics Agent"] += 1

        terms_needed = [name for name in ("quantity", "currency", "incoterm") if name in unresolved]
        if terms_needed:
            query = f'"{product}" tender quantity currency incoterm' if product else None
            tasks.append(_task(
                oid,
                "Source Terms Agent",
                "source_terms_required:" + ",".join(terms_needed),
                query,
                [
                    "read only official/source-backed notice or document text",
                    "capture labeled commercial term verbatim as structured value",
                    "store source field/provenance",
                    "leave absent fields unknown",
                ],
                90,
            ))
            agents["Source Terms Agent"] += 1

    tasks.sort(key=lambda t: (-int(t["priority"]), str(t.get("opportunity_id") or ""), t["assigned_agent"]))
    result = {
        "task_count": len(tasks),
        "agent_task_counts": dict(sorted(agents.items())),
        "tasks": tasks[:100],
        "queue_truncated": len(tasks) > 100,
        "source_backed_only": True,
        "external_outreach_enabled": False,
        "rule": "Research agents may collect evidence, but no price, freight, quantity, currency or Incoterm is accepted without explicit source-backed evidence.",
    }
    payload["commercial_research_agents"] = result
    return result
