from __future__ import annotations

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


HOME_URL = "https://www.ggzy.gov.cn/"
ALLOWED_HOSTS = {"www.ggzy.gov.cn", "ggzy.gov.cn"}
DEAL_RE = re.compile(r"/information/deal/html/", re.I)
GOODS_KEYWORDS = (
    "设备", "仪器", "仪表", "材料", "物资", "货物", "装备", "器材", "机械", "车辆",
    "家具", "服装", "药品", "试剂", "食品", "电源", "服务器", "计算机", "生产线",
    "医疗", "实验室", "零部件", "配件", "电缆", "电池", "光谱仪", "检测设备",
)
SERVICE_ONLY_HINTS = ("服务", "监理", "设计", "咨询", "审计", "培训", "施工", "工程", "租赁")


class AnchorParser(HTMLParser):
    BLOCK = {"p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "br", "section"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[dict[str, str]] = []
        self.lines: list[str] = []
        self.title_parts: list[str] = []
        self._buf: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        low = tag.lower()
        if low == "a":
            self._anchor_href = dict(attrs).get("href")
            self._anchor_text = []
        if low == "title":
            self._in_title = True
        if low in self.BLOCK:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        low = tag.lower()
        if low == "a" and self._anchor_href:
            label = " ".join(self._anchor_text).strip()
            self.anchors.append({"href": self._anchor_href, "text": label})
            self._anchor_href = None
            self._anchor_text = []
        if low == "title":
            self._in_title = False
        if low in self.BLOCK:
            self._flush()

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value:
            return
        if self._in_title:
            self.title_parts.append(value)
        if self._anchor_href is not None:
            self._anchor_text.append(value)
        self._buf.append(value)

    def _flush(self) -> None:
        if self._buf:
            line = " ".join(self._buf).strip()
            if line:
                self.lines.append(line)
        self._buf = []

    def finish(self) -> None:
        self._flush()


def parse_html(html: str) -> AnchorParser:
    parser = AnchorParser()
    parser.feed(html)
    parser.finish()
    return parser


def safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS


def fetch_html(url: str, timeout: float = 12.0, max_bytes: int = 1_500_000) -> str:
    if not safe_url(url):
        raise ValueError("unapproved China public resources host")
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GlobalBrokerResearch/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(max_bytes + 1)[:max_bytes]
        charset = response.headers.get_content_charset()
    for encoding in (charset, "utf-8", "gb18030", "gbk"):
        if not encoding:
            continue
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def is_goods_procurement(title: str) -> bool:
    if "采购" not in title:
        return False
    if any(keyword in title for keyword in GOODS_KEYWORDS):
        return True
    if any(keyword in title for keyword in SERVICE_ONLY_HINTS):
        return False
    return False


def discover_candidates(html: str, base_url: str = HOME_URL, limit: int = 30) -> list[dict[str, str]]:
    parser = parse_html(html)
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in parser.anchors:
        title = anchor.get("text", "").strip()
        url = urljoin(base_url, anchor.get("href", ""))
        if not safe_url(url) or not DEAL_RE.search(urlparse(url).path):
            continue
        if not is_goods_procurement(title):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "title": title})
        if len(out) >= limit:
            break
    return out


def _field(lines: list[str], labels: tuple[str, ...], max_len: int = 180) -> str:
    for idx, line in enumerate(lines):
        for label in labels:
            pos = line.find(label)
            if pos < 0:
                continue
            tail = line[pos + len(label):].lstrip("：: ")
            if tail:
                return tail[:max_len]
            if idx + 1 < len(lines):
                nxt = lines[idx + 1].strip()
                if nxt:
                    return nxt[:max_len]
    return ""


def _section(lines: list[str], starts: tuple[str, ...], stops: tuple[str, ...], max_chars: int = 5500) -> str:
    active = False
    out: list[str] = []
    for line in lines:
        if not active and any(marker in line for marker in starts):
            active = True
            out.append(line)
            continue
        if active:
            if any(marker in line for marker in stops):
                break
            out.append(line)
            if sum(len(x) for x in out) >= max_chars:
                break
    return "\n".join(out)[:max_chars]


def parse_detail(url: str, listed_title: str, html: str) -> dict[str, Any] | None:
    parser = parse_html(html)
    lines = [line for line in parser.lines if line]
    if not lines:
        return None
    page_title = " ".join(parser.title_parts).strip()
    title = listed_title or page_title
    if not is_goods_procurement(title):
        return None

    buyer = _field(lines, ("采购人", "采购单位", "招标人", "项目单位"))
    budget = _field(lines, ("预算金额", "预算", "最高限价", "项目金额", "招标控制价"))
    deadline = _field(lines, ("投标截止时间", "提交投标文件截止时间", "开标时间", "截止时间"))
    region = _field(lines, ("所在地区", "行政区域", "地域", "地区"), 80)
    project_code = _field(lines, ("项目编号", "招标编号", "采购编号"), 100)
    need = _section(
        lines,
        ("采购需求", "项目需求", "招标内容", "采购内容", "项目概况"),
        ("资格要求", "投标人资格", "获取招标文件", "招标文件的获取", "联系方式"),
    )
    excerpt = "\n".join(lines[:120])[:10000]
    if len(excerpt) < 80:
        return None

    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"ggzy:{digest}",
        "source": "National Public Resources Trading Platform (China)",
        "source_type": "official_national_public_resources_platform",
        "source_url": url,
        "official_url": url,
        "official_links": [url],
        "title_original": title,
        "title_tr": "Çin resmî alım ilanı — " + title,
        "detail_original": need or excerpt,
        "demand_summary_tr": "Çin Ulusal Kamu Kaynakları Ticaret Platformunda yayımlanan mal/ekipman alım kaydı. Teknik ve ticari koşullar resmî kaynak metni üzerinden doğrulanmalıdır.",
        "buyer-name": buyer,
        "buyer-country": "CHINA",
        "country_name": "China",
        "market_region": "Çin / Doğu Asya",
        "regionname": region or "China",
        "product_name": title,
        "estimated_value": budget,
        "deadline": deadline,
        "project_code": project_code,
        "contract-nature": "goods",
        "opportunity_type": "china_public_resources_goods_procurement",
        "translation_status": "pending_human_or_ai_translation",
        "market_access_status": "foreign_supplier_eligibility_review_required",
        "buyer_verified": False,
        "buyer_source_identified": bool(buyer),
        "technical-specification": need,
        "supplier_research": {
            "status": "dossier_enrichment_pending",
            "product_query": title,
            "verified_count": 0,
        },
        "workflow": {
            "buyer": {"status": "source_identified_due_diligence_pending" if buyer else "identity_pending", "verified": False},
            "supplier": {"status": "research_pending", "verified_candidates": 0},
            "china_market_research": {
                "status": "official_public_demand_found",
                "product_query": title,
                "goal": "Yabancı tedarikçi uygunluğu, ithalat hacmi ve alıcı erişimi doğrulanacak",
            },
        },
        "source_excerpt": excerpt,
    }


def collect(max_notices: int = 12) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[str] = []
    try:
        home = fetch_html(HOME_URL)
        candidates = discover_candidates(home, HOME_URL, limit=max_notices * 3)
    except HTTPError as exc:
        candidates = []
        errors.append(f"{HOME_URL}: HTTP {exc.code}")
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        candidates = []
        errors.append(f"{HOME_URL}: {type(exc).__name__}")

    results: list[dict[str, Any]] = []
    detail_failures = 0
    for candidate in candidates:
        try:
            item = parse_detail(candidate["url"], candidate["title"], fetch_html(candidate["url"]))
        except HTTPError as exc:
            detail_failures += 1
            errors.append(f"{candidate['url']}: HTTP {exc.code}")
            continue
        except (URLError, TimeoutError, ValueError, OSError):
            detail_failures += 1
            continue
        if item:
            results.append(item)
            if len(results) >= max_notices:
                break

    meta = {
        "source": HOME_URL,
        "status": "ok" if results else ("source_unavailable" if errors and not candidates else "no_tradeable_goods_found"),
        "candidate_goods_links": len(candidates),
        "goods_opportunities_added": len(results),
        "detail_failures": detail_failures,
        "errors": errors[:5],
        "foreign_supplier_eligibility_assumed": False,
    }
    return results, meta


def merge_payload(payload: dict[str, Any], max_notices: int = 12) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        opportunities = []
        payload["opportunities"] = opportunities
    items, meta = collect(max_notices=max_notices)
    known_urls = {
        str(item.get("source_url"))
        for item in opportunities
        if isinstance(item, dict) and item.get("source_url")
    }
    added = 0
    for item in items:
        if item["source_url"] in known_urls:
            continue
        opportunities.append(item)
        known_urls.add(item["source_url"])
        added += 1
    meta["goods_opportunities_added"] = added
    payload["china_ggzy_feed"] = meta
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.china_ggzy_feed <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = merge_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CHINA_GGZY_FEED " + json.dumps(payload.get("china_ggzy_feed") or {}, ensure_ascii=False, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    main()
