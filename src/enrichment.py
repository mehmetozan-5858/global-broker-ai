from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


# Conservative CPV family labels. These are used only to make source codes readable;
# the original code is always preserved and no detailed specification is invented.
CPV_FAMILIES = {
    "03": "Tarım, çiftçilik, balıkçılık ve ilgili ürünler",
    "09": "Petrol ürünleri, yakıt, elektrik ve diğer enerji kaynakları",
    "14": "Madencilik, temel metaller ve ilgili ürünler",
    "15": "Gıda, içecek, tütün ve ilgili ürünler",
    "18": "Giyim, ayakkabı, valiz ve aksesuarlar",
    "24": "Kimyasal ürünler",
    "30": "Ofis ve bilgisayar ekipmanları",
    "31": "Elektrikli makine, cihaz, ekipman ve sarf malzemeleri",
    "32": "Radyo, televizyon, iletişim ve telekomünikasyon ekipmanları",
    "33": "Medikal ekipman, ilaç ve kişisel bakım ürünleri",
    "34": "Taşıma ekipmanları ve yardımcı taşıma ürünleri",
    "35": "Güvenlik, yangın, polis ve savunma ekipmanları",
    "37": "Müzik aletleri, spor ürünleri, oyunlar ve oyuncaklar",
    "38": "Laboratuvar, optik ve hassas ölçüm ekipmanları",
    "39": "Mobilya, iç donanım, ev aletleri ve temizlik ürünleri",
    "42": "Endüstriyel makineler",
    "43": "Madencilik, taşocakçılığı ve inşaat makineleri",
    "44": "İnşaat yapıları, malzemeleri ve yardımcı ürünler",
    "45": "İnşaat işleri",
    "48": "Yazılım paketleri ve bilgi sistemleri",
    "50": "Tamir ve bakım hizmetleri",
    "60": "Taşımacılık hizmetleri",
}

CPV_EXACT = {
    "38000000": "Laboratuvar, optik ve hassas ölçüm ekipmanları",
    "38310000": "Hassas teraziler",
    "42931100": "Laboratuvar santrifüjleri ve aksesuarları",
}

GENERIC_TITLES = {
    "uluslararası satın alma talebi",
    "satın alma talebi",
    "procurement",
    "purchase",
    "supply",
}

URL_RE = re.compile(r"https?://[^\s\]\[\)\(\"'<>]+", re.I)
CPV_RE = re.compile(r"(?<!\d)(\d{8})(?!\d)")


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(filter(None, (text(v) for v in value))).strip()
    if isinstance(value, dict):
        return " ".join(filter(None, (text(v) for v in value.values()))).strip()
    return str(value).strip()


def first(item: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = text(item.get(key))
        if value:
            return value
    return ""


def unique(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip().rstrip(".,;)")
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def collect_urls(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.extend(URL_RE.findall(value))
    elif isinstance(value, list):
        for v in value:
            found.extend(collect_urls(v))
    elif isinstance(value, dict):
        for v in value.values():
            found.extend(collect_urls(v))
    return unique(found)


def cpv_codes(item: dict[str, Any]) -> list[str]:
    raw = " ".join(
        text(item.get(k))
        for k in (
            "classification-cpv",
            "additional-classification-lot",
            "categories",
            "title_original",
            "detail_original",
        )
    )
    return unique(CPV_RE.findall(raw))


def cpv_label(code: str) -> str:
    if code in CPV_EXACT:
        return CPV_EXACT[code]
    return CPV_FAMILIES.get(code[:2], "CPV ürün/hizmet grubu")


def readable_cpv(item: dict[str, Any]) -> list[dict[str, str]]:
    return [{"code": code, "label_tr": cpv_label(code)} for code in cpv_codes(item)]


def derive_product_name(item: dict[str, Any], cpv: list[dict[str, str]]) -> str:
    explicit = first(item, ["product_name", "product", "item_name", "goods_name"])
    if explicit:
        return explicit

    title = first(item, ["title_tr", "title_original", "notice-title"])
    if title and title.lower().strip() not in GENERIC_TITLES and not title.isdigit():
        return title

    labels = unique([x["label_tr"] for x in cpv if x.get("label_tr")])
    if labels:
        return " / ".join(labels[:3])
    return ""


def derive_quantity(item: dict[str, Any]) -> str:
    quantity = first(item, ["quantity", "quantity-lot", "estimated_quantity", "volume"])
    unit = first(item, ["quantity-unit-lot", "unit", "quantity_unit"])
    if quantity and unit and unit.lower() not in quantity.lower():
        return f"{quantity} {unit}"
    return quantity


def derive_budget(item: dict[str, Any]) -> dict[str, str | None]:
    value = first(
        item,
        [
            "estimated-value-lot",
            "estimated-value-proc",
            "estimated-value-procurement",
            "estimated_value",
            "budget",
            "amount",
            "value",
        ],
    )
    currency = first(item, ["estimated-value-cur-proc", "currency-lot", "currency", "currency_code"])
    return {"value": value or None, "currency": currency or None}


def derive_delivery(item: dict[str, Any]) -> str:
    city = first(item, ["place-of-performance-city-lot", "delivery_city", "city"])
    country = first(
        item,
        [
            "place-of-performance-country-lot",
            "delivery_country",
            "buyer-country",
            "buyer_country",
            "project_ctry_name",
        ],
    )
    other = first(item, ["place-of-performance-other-lot", "delivery_location", "place-of-performance"])
    return ", ".join(unique([city, country, other]))


def derive_links(item: dict[str, Any]) -> list[str]:
    keys = [
        "links",
        "source_url",
        "url",
        "notice_url",
        "official_url",
        "document_url",
        "documents_url",
        "tender_url",
        "submission-url-lot",
        "buyer-touchpoint-internet-address",
    ]
    urls: list[str] = []
    for key in keys:
        urls.extend(collect_urls(item.get(key)))
    return unique(urls)


def dossier_missing(dossier: dict[str, Any]) -> list[str]:
    required = {
        "buyer": dossier.get("buyer_name"),
        "product": dossier.get("product_name"),
        "demand_description": dossier.get("demand_description"),
        "quantity": dossier.get("quantity"),
        "deadline": dossier.get("deadline"),
        "official_source": dossier.get("official_links"),
    }
    return [name for name, value in required.items() if not value]


def enrich_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    cpv = readable_cpv(item)
    links = derive_links(item)
    budget = derive_budget(item)
    product_name = derive_product_name(item, cpv)
    demand_description = first(
        item,
        ["detail_tr", "demand_summary_tr", "detail_original", "description-lot", "title_tr", "title_original"],
    )

    dossier = {
        "buyer_name": first(item, ["buyer-name", "buyer", "project_name", "organization_name"]) or None,
        "buyer_country": first(item, ["buyer-country", "buyer_country", "project_ctry_name", "country_name"]) or None,
        "product_name": product_name or None,
        "demand_description": demand_description or None,
        "quantity": derive_quantity(item) or None,
        "budget_value": budget["value"],
        "budget_currency": budget["currency"],
        "delivery_location": derive_delivery(item) or None,
        "deadline": first(item, ["deadline-receipt-tender-date-lot", "submission_deadline_date", "deadline_date", "deadline"]) or None,
        "procedure_type": first(item, ["procedure-type", "procurement_method", "notice_type"]) or None,
        "contract_nature": first(item, ["contract-nature", "procurement_category"]) or None,
        "cpv": cpv,
        "official_links": links,
        "source": first(item, ["source"]) or None,
    }
    missing = dossier_missing(dossier)
    completeness = round((6 - len(missing)) / 6 * 100)
    dossier["missing_fields"] = missing
    dossier["completeness_percent"] = completeness
    dossier["supplier_sourcing_ready"] = completeness >= 67 and bool(dossier["product_name"] and dossier["demand_description"])

    item["dossier"] = dossier
    if product_name:
        item["product_name"] = product_name
    if dossier["quantity"]:
        item["quantity"] = dossier["quantity"]
    if budget["value"]:
        item["estimated_value"] = budget["value"]
    if budget["currency"]:
        item["currency"] = budget["currency"]
    if dossier["delivery_location"]:
        item["delivery_location"] = dossier["delivery_location"]
    if links:
        item["official_links"] = links
        item.setdefault("document_url", links[0])

    # Replace raw-code supplier search with a human-readable source-derived product query.
    supplier = item.get("supplier_research")
    if isinstance(supplier, dict):
        supplier["product_query"] = product_name or first(item, ["title_tr", "title_original"])
        supplier["dossier_ready"] = dossier["supplier_sourcing_ready"]
        supplier["blocked_by_missing_fields"] = missing
        if not dossier["supplier_sourcing_ready"]:
            supplier["status"] = "dossier_enrichment_pending"

    workflow = item.get("workflow")
    if isinstance(workflow, dict):
        workflow["opportunity_dossier"] = {
            "status": "ready_for_supplier_research" if dossier["supplier_sourcing_ready"] else "enrichment_pending",
            "completeness_percent": completeness,
            "missing_fields": missing,
        }
        if item.get("market_region") == "Çin / Doğu Asya":
            workflow["china_market_research"] = {
                "status": "demand_validation_pending",
                "product_query": product_name or None,
                "goal": "Çin ithalat talebi, hacim, alıcı ve resmi kaynaklarla doğrulanacak",
            }

    return item


def enrich_payload(payload: dict[str, Any]) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        return payload
    enriched = []
    for item in opportunities:
        if isinstance(item, dict):
            enriched.append(enrich_opportunity(item))
        else:
            enriched.append(item)
    payload["opportunities"] = enriched
    payload["enrichment"] = {
        "version": 1,
        "mode": "source_only_no_hallucination",
        "enriched_count": sum(1 for x in enriched if isinstance(x, dict)),
    }
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.enrichment <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = enrich_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
