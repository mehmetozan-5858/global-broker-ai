from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _status(item: dict[str, Any], key: str) -> str:
    return str(item.get(key) or "").strip().lower()


def _sales_priority(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("sales_priority")
    return value if isinstance(value, dict) else {}


def _is_spec_ready(item: dict[str, Any]) -> bool:
    if item.get("supplier_ready") is True:
        return True
    spec = item.get("specification")
    if not isinstance(spec, dict):
        spec = item.get("specification_analysis")
    if not isinstance(spec, dict):
        return False
    if spec.get("supplier_ready") is True:
        return True
    status = str(spec.get("status") or spec.get("readiness") or "").lower()
    return status in {"ready", "supplier_ready", "complete", "parsed", "narrative_ready"}


def _buyer_verified(item: dict[str, Any]) -> bool:
    priority = _sales_priority(item)
    reasons = priority.get("reasons") if isinstance(priority.get("reasons"), list) else []
    return "verified_buyer" in reasons


def next_action(item: dict[str, Any]) -> dict[str, Any]:
    """Return the highest-value next action needed to move an opportunity toward closing.

    This is a work queue, not a claim that a deal will close. It never upgrades a
    verification/compliance/margin fact on its own.
    """
    priority = _sales_priority(item)
    grade = str(priority.get("grade") or "C").upper()

    if grade == "A":
        return {
            "action": "prepare_offer_and_contact",
            "label_tr": "Teklif ve iletişim hazırlığı",
            "owner": "Communication + Negotiation",
            "urgency": "high",
        }

    if not _is_spec_ready(item):
        return {
            "action": "complete_specification",
            "label_tr": "Şartname / ürün ihtiyacını tamamla",
            "owner": "Opportunity + Document",
            "urgency": "high",
        }

    if not _buyer_verified(item):
        return {
            "action": "verify_buyer",
            "label_tr": "Alıcıyı doğrula",
            "owner": "Risk",
            "urgency": "high",
        }

    if _status(item, "supplier_status") != "verified":
        return {
            "action": "verify_supplier",
            "label_tr": "Uygun tedarikçiyi bul ve doğrula",
            "owner": "Supplier",
            "urgency": "high",
        }

    if _status(item, "compliance_status") != "clear":
        return {
            "action": "clear_compliance",
            "label_tr": "Uygunluk / ihracat riskini temizle",
            "owner": "Trade + Risk",
            "urgency": "medium",
        }

    if _status(item, "margin_status") != "positive":
        return {
            "action": "confirm_margin",
            "label_tr": "Fiyat, lojistik ve komisyon marjını doğrula",
            "owner": "Price + Logistics",
            "urgency": "medium",
        }

    return {
        "action": "recalculate_priority",
        "label_tr": "Satış önceliğini yeniden hesapla",
        "owner": "CEO",
        "urgency": "medium",
    }


def acceleration_score(item: dict[str, Any]) -> int:
    """Rank which blocked opportunity should receive effort first.

    This score measures work priority, not buyer/supplier verification or deal
    probability. Source-backed readiness gets more weight; missing facts do not.
    """
    score = 0
    if _is_spec_ready(item):
        score += 45
    if str(item.get("source_url") or "").startswith("http"):
        score += 10
    if item.get("estimated_value") not in (None, "", 0):
        score += 15
    if str(item.get("deadline") or "").strip():
        score += 10
    if str(item.get("product_name") or item.get("readable_product") or item.get("title_tr") or "").strip():
        score += 10
    region = str(item.get("market_region") or "").lower()
    country = str(item.get("buyer_country") or item.get("country") or "").lower()
    if "çin" in region or "china" in country or "cn" == country.strip():
        score += 5
    if _buyer_verified(item):
        score += 5
    return min(score, 100)


def enrich_payload(payload: dict[str, Any], top_n: int = 25) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload

    action_counts: Counter[str] = Counter()
    queue: list[dict[str, Any]] = []

    for item in opportunities:
        if not isinstance(item, dict):
            continue
        action = next_action(item)
        score = acceleration_score(item)
        item["sales_acceleration"] = {
            **action,
            "work_priority_score": score,
            "does_not_claim_close_probability": True,
        }
        action_counts[action["action"]] += 1
        queue.append({
            "source": item.get("source"),
            "source_id": item.get("source_id") or item.get("id"),
            "title_tr": item.get("title_tr") or item.get("title_original") or item.get("title"),
            "buyer": item.get("buyer"),
            "buyer_country": item.get("buyer_country") or item.get("country"),
            "market_region": item.get("market_region"),
            "sales_grade": (_sales_priority(item).get("grade") or "C"),
            "next_action": action["action"],
            "next_action_tr": action["label_tr"],
            "owner": action["owner"],
            "work_priority_score": score,
            "source_url": item.get("source_url"),
        })

    queue.sort(key=lambda row: (-int(row["work_priority_score"]), str(row.get("source_id") or "")))
    payload["sales_acceleration_summary"] = {
        "version": 1,
        "strategy": "move_source_backed_opportunities_toward_close",
        "action_counts": dict(action_counts),
        "top_queue": queue[:top_n],
        "top_queue_size": min(top_n, len(queue)),
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.sales_acceleration <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    enrich_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = payload.get("sales_acceleration_summary") or {}
    counts = summary.get("action_counts") or {}
    print("SALES_ACCELERATION_SUMMARY " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())), file=sys.stderr)


if __name__ == "__main__":
    main()
