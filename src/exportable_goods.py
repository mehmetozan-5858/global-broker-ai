"""Conservative physical-goods eligibility for Global Broker.

Only source-backed physical product procurements may become commercial candidates.
Services, construction/works and digital-only procurements are excluded. Mixed or
ambiguous records are quarantined for review instead of being promoted.
"""
from __future__ import annotations

import re
from typing import Any

SERVICE = re.compile(
    r"\b(?:consult(?:ant|ancy|ing)?|engineering services?|architect(?:ure|ural)? services?|"
    r"personnel|staff(?:ing)?|recruitment|training|audit(?:ing)?|technical assistance|"
    r"feasibility study|drilling services?|well drilling|maintenance services?|repair services?|"
    r"cleaning services?|security services?|transport services?|logistics services?|"
    r"construction works?|civil works?|works contract|service contract|professional services?|"
    r"project management|supervision services?|insurance services?|legal services?|"
    r"hizmet(?:leri)?|danışmanlık|mühendislik hizmet(?:i|leri)?|personel|istihdam|eğitim hizmeti|"
    r"sondaj hizmeti|bakım hizmeti|onarım hizmeti|inşaat işi|yapım işi)\b",
    re.I,
)

# Installation/commissioning/support alongside goods does not make an opportunity pure goods.
MIXED_ADJUNCT = re.compile(
    r"\b(?:installation|installing|commissioning|integration|configuration|implementation|"
    r"maintenance|repair|training|technical support|after[- ]sales service|design and build|"
    r"engineering|turnkey|kurulum|montaj|devreye alma|entegrasyon|bakım|onarım|eğitim|"
    r"teknik destek|anahtar teslim)\b",
    re.I,
)

NON_PHYSICAL = re.compile(
    r"\b(?:software(?: licence| license| subscription)?|saas|cloud services?|cloud subscription|"
    r"digital subscription|data subscription|online platform|mobile application development|"
    r"web development|source code|intellectual property|lisans aboneliği|yazılım aboneliği|"
    r"bulut hizmeti|dijital abonelik)\b",
    re.I,
)

GOODS = re.compile(
    r"\b(?:goods|supplies|equipment|machinery|machines?|raw materials?|physical materials?|products?|"
    r"spare parts?|vehicles?|furniture|medical devices?|medicines?|pharmaceuticals?|textiles?|"
    r"garments?|chemicals?|food|grain|steel|cables?|generators?|computers?|servers?|laptops?|"
    r"network equipment|desks?|chairs?|beds?|pumps?|pipes?|tools?|instruments?|consumables?|"
    r"procurement of goods|supply and delivery|purchase and delivery|temini|tedariki|mal alımı|"
    r"ekipman|makine|ham madde|fiziksel malzeme|ürün|yedek parça|araç|mobilya|ilaç|gıda|"
    r"kablo|jeneratör|bilgisayar|masa|sandalye|ranza|pompa|boru)\b",
    re.I,
)

GOODS_TYPES = {
    "goods", "supply", "supplies", "mal alımı", "mal alimi", "goods contract",
    "goods and supplies", "supply contract",
}
SERVICE_TYPES = {
    "services", "service", "works", "consulting services", "consultancy", "consulting",
    "hizmet", "hizmet alımı", "construction", "works contract", "services contract",
}


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_text(x) for x in value.values())
    if isinstance(value, list):
        return " ".join(_text(x) for x in value)
    return str(value or "").strip()


def _source_type(item: dict[str, Any]) -> str:
    value = next(
        (
            item[k]
            for k in (
                "contract-nature",
                "procurement_category",
                "procurement_type",
                "contract_type",
                "contract-nature-lot",
            )
            if item.get(k)
        ),
        "",
    )
    return _text(value).lower().strip()


def _headline(item: dict[str, Any]) -> str:
    return _text(
        item.get("title_original")
        or item.get("title_tr")
        or item.get("bid_description")
        or item.get("notice-title")
        or item.get("title")
    )


def _detail(item: dict[str, Any]) -> str:
    return " ".join(
        x
        for x in (
            _headline(item),
            _text(item.get("detail_original")),
            _text(item.get("description-lot")),
            _text(item.get("procurement_category")),
            _text(item.get("contract-nature")),
        )
        if x
    )


def classify(item: dict[str, Any]) -> dict[str, str]:
    typ = _source_type(item)
    headline = _headline(item)
    evidence_text = _detail(item)

    explicit_service_type = typ in SERVICE_TYPES or any(
        marker in typ for marker in ("consulting service", "works contract", "construction works")
    )
    explicit_goods_type = typ in GOODS_TYPES or typ in {"supplies", "goods"}

    headline_goods = bool(GOODS.search(headline))
    any_goods = bool(GOODS.search(evidence_text))
    service = bool(SERVICE.search(evidence_text))
    mixed_adjunct = bool(MIXED_ADJUNCT.search(evidence_text))
    non_physical = bool(NON_PHYSICAL.search(evidence_text))

    # Authoritative source classification wins over keyword optimism.
    if explicit_service_type:
        return {
            "status": "exclude_service",
            "reason": "Kaynak ihale türü hizmet, danışmanlık veya yapım olarak bildiriyor.",
            "basis": "source_type",
        }

    if non_physical and not headline_goods:
        return {
            "status": "exclude_non_physical",
            "reason": "İlan dijital/yazılım ağırlıklı; fiziksel ürün ticareti kanıtlanmadı.",
            "basis": "non_physical_signal",
        }

    if explicit_goods_type:
        if service or mixed_adjunct or non_physical:
            return {
                "status": "review_mixed",
                "reason": "Kaynak mal alımı diyor ancak hizmet, kurulum, destek veya dijital unsur da içeriyor.",
                "basis": "source_goods_with_mixed_signal",
            }
        return {
            "status": "goods_candidate",
            "reason": "Kaynak fiziksel mal alımı olarak sınıflandırıyor; ihracat ve katılım koşulları ayrıca doğrulanmalı.",
            "basis": "source_goods_type",
        }

    if any_goods and (service or mixed_adjunct or non_physical):
        return {
            "status": "review_mixed",
            "reason": "Kayıtta hem fiziksel ürün hem hizmet/kurulum/dijital unsur bulunuyor.",
            "basis": "mixed_text_signals",
        }

    if service:
        return {
            "status": "exclude_service",
            "reason": "İlan hizmet, personel, danışmanlık veya yapım işi içeriyor.",
            "basis": "service_signal",
        }

    if non_physical:
        return {
            "status": "exclude_non_physical",
            "reason": "Fiziksel teslimat yerine yazılım/dijital hizmet sinyali bulunuyor.",
            "basis": "non_physical_signal",
        }

    # Title-level physical product evidence is required when source type is absent.
    if headline_goods:
        return {
            "status": "goods_candidate",
            "reason": "Başlık fiziksel ürün tedarikine açıkça işaret ediyor; kaynak türü ve ihracat koşulları teyit edilmeli.",
            "basis": "headline_goods_signal",
        }

    return {
        "status": "review_unknown",
        "reason": "İlanın fiziksel mal alımı olduğu henüz kanıtlanamadı.",
        "basis": "insufficient_evidence",
    }
