"""Non-binding, evidence-first B2B offer / negotiation / contract preparation.

All outputs are internal Shadow Mode drafts. This module cannot send messages,
execute transactions, or sign contracts. Unknown commercial terms stay unknown.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

@dataclass(frozen=True)
class DealBrief:
    opportunity_id: str
    product: str
    buyer_company: str = ""
    supplier_company: str = ""
    buyer_country: str = ""
    supplier_country: str = ""
    quantity: str = ""
    unit: str = ""
    grade_specification: str = ""
    incoterm: str = ""
    named_port_or_place: str = ""
    unit_price: Optional[str] = None
    currency: str = ""
    payment_terms: str = ""
    delivery_terms: str = ""
    source_url: str = ""
    buyer_verified: bool = False
    supplier_verified: bool = False
    price_quote_verified: bool = False
    counterparty_contact_consent: bool = False

def _valid_price(value: Optional[str]) -> Optional[str]:
    if value is None or not str(value).strip():
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number < 0:
        return None
    return str(number)

def _field(value: str, placeholder: str = "[DOĞRULAMA BEKLİYOR]") -> str:
    return str(value).strip() if value and str(value).strip() else placeholder

def _readiness(deal: DealBrief) -> list[str]:
    missing = []
    if not deal.opportunity_id.strip() or not deal.source_url.strip():
        missing.append("opportunity_source")
    if not deal.product.strip():
        missing.append("product")
    if not deal.buyer_verified:
        missing.append("buyer_verification")
    if not deal.supplier_verified:
        missing.append("supplier_verification")
    if not deal.counterparty_contact_consent:
        missing.append("contact_consent")
    if not deal.quantity.strip() or not deal.unit.strip():
        missing.append("quantity_and_unit")
    if not deal.grade_specification.strip():
        missing.append("technical_specification")
    if not deal.incoterm.strip() or not deal.named_port_or_place.strip():
        missing.append("incoterm_and_named_place")
    if _valid_price(deal.unit_price) is None or not deal.currency.strip() or not deal.price_quote_verified:
        missing.append("verified_price_quote")
    if not deal.payment_terms.strip():
        missing.append("payment_terms")
    if not deal.delivery_terms.strip():
        missing.append("delivery_terms")
    return missing

def prepare_sales_pack(deal: DealBrief, *, proposed_commission_rate: Optional[str] = None,
                       protection_months: int = 12) -> dict:
    if protection_months not in (12, 24, 36):
        raise ValueError("protection period must be 12, 24, or 36 months")
    if proposed_commission_rate is not None:
        rate = _valid_price(proposed_commission_rate)
        if rate is None or Decimal(rate) > 100:
            raise ValueError("commission proposal must be a valid 0-100 percentage")
    missing = _readiness(deal)
    price = _valid_price(deal.unit_price) if deal.price_quote_verified else None
    displayed_price = (price + " " + deal.currency.strip()) if price is not None and deal.currency.strip() else "[DOĞRULANMIŞ FİYAT TEKLİFİ BEKLENİYOR]"
    lines = [
        "TİCARİ TEKLİF TASLAĞI — GÖNDERİLMEDİ / BAĞLAYICI DEĞİLDİR",
        "Fırsat: " + _field(deal.opportunity_id),
        "Ürün: " + _field(deal.product),
        "Alıcı: " + _field(deal.buyer_company),
        "Tedarikçi: " + _field(deal.supplier_company),
        "Miktar: " + _field(deal.quantity) + " " + _field(deal.unit),
        "Teknik şartname: " + _field(deal.grade_specification),
        "Birim fiyat: " + displayed_price,
        "Incoterms: " + _field(deal.incoterm) + " / " + _field(deal.named_port_or_place),
        "Ödeme: " + _field(deal.payment_terms),
        "Teslimat: " + _field(deal.delivery_terms),
        "Kaynak: " + _field(deal.source_url),
    ]
    negotiation = [
        "Ürün standardı, toleranslar, miktar ve MOQ teyidi",
        "Gerçek fiyat teklifinin tarihi, geçerliliği ve para birimi",
        "Incoterms sürümü, adlandırılmış teslim yeri, sigorta ve navlun",
        "Ödeme güvencesi, belge şartları ve teslim takvimi",
        "İki tarafın aracılık ve iletişim yetkisi",
    ]
    contract_fields = {
        "buyer_legal_entity": _field(deal.buyer_company),
        "supplier_legal_entity": _field(deal.supplier_company),
        "broker_legal_entity": "[ARACI TÜZEL KİŞİ/KİŞİ]",
        "scope_and_product": _field(deal.product),
        "first_transaction_in_scope": "explicit_contract_clause_required",
        "repeat_transactions_in_scope": "explicit_contract_clause_required",
        "protection_months_proposed": protection_months,
        "non_circumvention": "legal_drafting_required",
        "commission_rate_proposal": proposed_commission_rate or "[MÜZAKERE EDİLECEK]",
        "commission_payer": "[ALICI / TEDARİKÇİ / AYRI MUTABAKAT]",
        "commission_trigger": "[SÖZLEŞMEDE TANIMLANACAK]",
        "collection_evidence": "[BANKA / MUHASEBE KANITI]",
        "governing_law": "[HUKUKÇU ONAYI]",
        "tax_and_invoicing": "[VERGİ UZMANI ONAYI]",
        "sanctions_and_compliance": "[UYUM ONAYI]",
        "dispute_resolution": "[HUKUKÇU ONAYI]",
        "enforceability": "[HUKUKÇU ONAYI]",
    }
    return {
        "mode": "shadow",
        "status": "INTERNAL_DRAFT_REVIEW_REQUIRED",
        "external_actions_allowed": False,
        "binding_offer": False,
        "offer_text_tr": "\n".join(lines),
        "negotiation_checklist_tr": negotiation,
        "contract_intake_fields": contract_fields,
        "missing_evidence": missing,
        "ready_for_external_contact": False,
        "commission_rate_basis": "negotiable_proposal_not_market_fact",
        "legal_review_required": True,
        "human_approval_required": True,
    }
