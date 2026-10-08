from __future__ import annotations

import json
import math
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
CHINA = "156"
WORLD = "0"
TURKEY = "792"
RETRY_DELAYS_SECONDS = (5.0, 15.0)

# Focus basket for Turkey-linked export opportunities. The HS label is intentionally
# broad; exact tariff/subheading eligibility still requires deal-level review.
PRODUCTS = {
    "1206": "Ayçiçeği tohumu",
    "1512": "Ayçiçeği, aspir ve pamuk tohumu yağları",
    "2515": "Mermer, traverten ve benzeri doğal taşlar",
    "2516": "Granit, kumtaşı ve diğer yapı taşları",
    "2523": "Çimento",
    "2603": "Bakır cevherleri ve konsantreleri",
    "2610": "Krom cevherleri ve konsantreleri",
    "2840": "Boratlar ve peroksoboratlar",
    "0802": "Diğer kabuklu meyveler (fındık dahil)",
    "1509": "Zeytinyağı ve fraksiyonları",
    "6802": "İşlenmiş anıtsal/yapı taşları ve ürünleri",
    "3102": "Azotlu mineral/kimyasal gübreler",
    "7208": "Sıcak haddelenmiş yassı demir/çelik ürünleri",
    "8419": "Isıl işlem ve proses makineleri",
    "8479": "Başka yerde belirtilmeyen makine ve mekanik cihazlar",
    "8708": "Motorlu taşıt parça ve aksesuarları",
}


def _year_candidates(today: date | None = None) -> list[tuple[int, int]]:
    today = today or date.today()
    latest = today.year - 1
    return [(latest, latest - 1), (latest - 1, latest - 2)]


def _request_payload(period: int, partner: str, timeout: float) -> dict[str, Any]:
    params = {
        "reporterCode": CHINA,
        "period": str(period),
        "flowCode": "M",
        "partnerCode": partner,
        "partner2Code": WORLD,
        "cmdCode": ",".join(PRODUCTS),
        "customsCode": "C00",
        "motCode": "0",
        "maxRecords": "500",
    }
    url = API + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "GlobalBrokerResearch/1.0", "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as response:
        raw = response.read(5_000_000)
    return json.loads(raw.decode("utf-8"))


def _retry_delay(exc: HTTPError, retry_index: int) -> float:
    header = None
    try:
        header = exc.headers.get("Retry-After") if exc.headers else None
    except Exception:
        header = None
    if header:
        try:
            return max(1.0, min(30.0, float(header)))
        except (TypeError, ValueError):
            pass
    return RETRY_DELAYS_SECONDS[min(retry_index, len(RETRY_DELAYS_SECONDS) - 1)]


def _fetch(period: int, partner: str, timeout: float = 20.0) -> dict[str, Any]:
    last_error: HTTPError | None = None
    attempts = len(RETRY_DELAYS_SECONDS) + 1
    for attempt in range(attempts):
        try:
            return _request_payload(period, partner, timeout)
        except HTTPError as exc:
            last_error = exc
            if exc.code != 429 or attempt >= attempts - 1:
                raise
            time.sleep(_retry_delay(exc, attempt))
    if last_error is not None:
        raise last_error
    raise RuntimeError("unreachable_fetch_state")


def _records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    return data if isinstance(data, list) else []


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _map_records(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("cmdCode") or row.get("cmdCodeAgg") or "").strip()
        if code not in PRODUCTS:
            continue
        current = out.get(code)
        value = _num(row.get("primaryValue")) or 0.0
        if current is None or value > (_num(current.get("primaryValue")) or 0.0):
            out[code] = row
    return out


def _growth(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round((current / previous - 1.0) * 100.0, 2)


def _safe_ratio(part: float | None, total: float | None) -> float | None:
    if part is None or total in (None, 0):
        return None
    return round(part / total * 100.0, 4)


def _signal_score(value_usd: float | None, growth_pct: float | None, turkey_share: float | None) -> int:
    if not value_usd or value_usd <= 0:
        return 0
    value_component = min(60.0, max(0.0, math.log10(value_usd + 1) - 5.0) * 15.0)
    growth_component = 0.0 if growth_pct is None else max(-10.0, min(25.0, growth_pct / 4.0))
    share_component = 0.0
    if turkey_share is not None:
        if 0 < turkey_share < 1:
            share_component = 15.0
        elif turkey_share < 5:
            share_component = 10.0
        elif turkey_share < 20:
            share_component = 5.0
    return int(max(0, min(100, round(value_component + growth_component + share_component))))


def build_radar_from_payloads(
    world_current: dict[str, Any],
    world_previous: dict[str, Any],
    turkey_current: dict[str, Any],
    current_year: int,
    previous_year: int,
) -> list[dict[str, Any]]:
    wc = _map_records(_records(world_current))
    wp = _map_records(_records(world_previous))
    tc = _map_records(_records(turkey_current))
    items: list[dict[str, Any]] = []

    for code, label in PRODUCTS.items():
        a = wc.get(code, {})
        b = wp.get(code, {})
        t = tc.get(code, {})
        current_value = _num(a.get("primaryValue"))
        previous_value = _num(b.get("primaryValue"))
        turkey_value = _num(t.get("primaryValue"))
        net_weight = _num(a.get("netWgt"))
        quantity = _num(a.get("qty"))
        growth = _growth(current_value, previous_value)
        share = _safe_ratio(turkey_value, current_value)
        unit_value_per_kg = None
        if current_value is not None and net_weight not in (None, 0):
            unit_value_per_kg = round(current_value / net_weight, 4)

        items.append({
            "hs4": code,
            "product_tr": label,
            "product_source_description": a.get("cmdDesc") or b.get("cmdDesc") or None,
            "current_year": current_year,
            "previous_year": previous_year,
            "china_import_value_usd": current_value,
            "previous_import_value_usd": previous_value,
            "yoy_growth_percent": growth,
            "china_import_net_weight_kg": net_weight,
            "china_import_quantity": quantity,
            "quantity_unit": a.get("qtyUnitAbbr") or None,
            "unit_value_usd_per_kg": unit_value_per_kg,
            "imports_from_turkey_usd": turkey_value,
            "turkey_share_percent": share,
            "signal_score": _signal_score(current_value, growth, share),
            "signal_type": "market_demand_not_buyer",
            "buyer_identified": False,
            "source": "UN Comtrade public preview API",
        })

    items.sort(key=lambda x: (x["signal_score"], x["china_import_value_usd"] or 0), reverse=True)
    return items


def collect_radar(today: date | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[str] = []
    for current_year, previous_year in _year_candidates(today):
        try:
            wc = _fetch(current_year, WORLD)
            wp = _fetch(previous_year, WORLD)
            tc = _fetch(current_year, TURKEY)
            items = build_radar_from_payloads(wc, wp, tc, current_year, previous_year)
            with_data = sum(1 for x in items if x["china_import_value_usd"] not in (None, 0))
            if with_data:
                return items, {
                    "status": "ok",
                    "current_year": current_year,
                    "previous_year": previous_year,
                    "products_monitored": len(PRODUCTS),
                    "products_with_data": with_data,
                    "source": API,
                    "buyer_data_inferred": False,
                }
            errors.append(f"{current_year}: no records for monitored products")
        except HTTPError as exc:
            errors.append(f"{current_year}: HTTP {exc.code}")
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{current_year}: {type(exc).__name__}")
    return [], {
        "status": "source_unavailable",
        "products_monitored": len(PRODUCTS),
        "products_with_data": 0,
        "source": API,
        "errors": errors[:4],
        "buyer_data_inferred": False,
    }


def _fallback_radar(fallback_payload: dict[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    if not isinstance(fallback_payload, dict):
        return None
    radar = fallback_payload.get("china_import_radar")
    if not isinstance(radar, dict):
        return None
    items = radar.get("items")
    meta = radar.get("meta")
    if not isinstance(items, list) or not items or not isinstance(meta, dict):
        return None
    if not any(isinstance(x, dict) and x.get("china_import_value_usd") not in (None, 0) for x in items):
        return None
    return items, meta


def merge_payload(payload: dict[str, Any], fallback_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    items, meta = collect_radar()
    if not items:
        fallback = _fallback_radar(fallback_payload)
        if fallback:
            old_items, old_meta = fallback
            failure_meta = meta
            meta = dict(old_meta)
            meta.update({
                "status": "stale_last_known_good",
                "fresh_fetch_status": failure_meta.get("status"),
                "fresh_fetch_errors": failure_meta.get("errors", []),
                "buyer_data_inferred": False,
            })
            items = old_items
    payload["china_import_radar"] = {"meta": meta, "items": items}
    return payload


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        raise SystemExit("usage: python -m src.china_import_radar <json-file> [last-known-good-json]")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    fallback_payload = None
    if len(sys.argv) == 3:
        fallback_path = Path(sys.argv[2])
        if fallback_path.exists() and fallback_path.stat().st_size:
            try:
                fallback_payload = json.loads(fallback_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                fallback_payload = None
    payload = merge_payload(payload, fallback_payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CHINA_IMPORT_RADAR " + json.dumps(payload["china_import_radar"]["meta"], ensure_ascii=False, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    main()
