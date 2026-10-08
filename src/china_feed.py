from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


INDEX_URLS = [
    "https://www.ccgp.gov.cn/cggg/zygg/gkzb/index.htm",
    "https://www.ccgp.gov.cn/cggg/dfgg/gkzb/index.htm",
]
ALLOWED_HOSTS = {"www.ccgp.gov.cn", "ccgp.gov.cn"}
NOTICE_RE = re.compile(r"/cggg/(?:zygg|dfgg)/gkzb/\d{6}/t\d+_\d+\.htm$", re.I)

GOODS_KEYWORDS = (
    "设备", "仪器", "仪表", "材料", "物资", "货物", "装备", "器材", "机械", "车辆",
    "家具", "服装", "药品", "试剂", "食品", "电源", "服务器", "计算机", "网络设备",
    "医疗设备", "实验室", "系统设备", "零部件", "配件", "组件", "电缆", "电池",
)
SERVICE_ONLY_HINTS = ("服务", "运维", "维护", "咨询", "审计", "培训", "工程", "施工", "装修")


class PageParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "br", "section"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.lines: list[str] = []
        self._buf: list[str] = []
        self._in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() in self.BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        if tag.lower() in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value:
            return
        if self._in_title:
            self.title_parts.append(value)
        self._buf.append(value)

    def _flush(self) -> None:
        if not self._buf:
            return
        value = " ".join(self._buf).strip()
        if value:
            self.lines.append(value)
        self._buf = []

    def finish(self) -> None:
        self._flush()



def _safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS


def fetch_html(url: str, timeout: float = 12.0, max_bytes: int = 1_500_000) -> str:
    if not _safe_url(url):
        raise ValueError("unapproved China procurement host")
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GlobalBrokerResearch/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raw = raw[:max_bytes]
        content_type = (response.headers.get("Content-Type") or "").lower()
        charset = response.headers.get_content_charset()
    candidates = [charset, "utf-8", "gb18030", "gbk"]
    for enc in candidates:
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def parse_html(html: str) -> PageParser:
    parser = PageParser()
    parser.feed(html)
    parser.finish()
    return parser


def discover_notice_urls(index_html: str, base_url: str) -> list[str]:
    parser = parse_html(index_html)
    out: list[str] = []
    seen: set[str] = set()
    for href in parser.links:
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if not _safe_url(url) or not NOTICE_RE.search(parsed.path):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def _field(lines: list[str], labels: tuple[str, ...], max_len: int = 160) -> str:
    for idx, line in enumerate(lines):
        compact = line.strip()
        for label in labels:
            pos = compact.find(label)
            if pos < 0:
                continue
            tail = compact[pos + len(label):].lstrip("：: ")
            if tail:
                return tail[:max_len]
            if idx + 1 < len(lines):
                nxt = lines[idx + 1].strip()
                if nxt:
                    return nxt[:max_len]
    return ""


def _section(lines: list[str], starts: tuple[str, ...], stops: tuple[str, ...], max_chars: int = 5000) -> str:
    active = False
    buf: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not active and any(start in stripped for start in starts):
            active = True
            after = stripped
            if after:
                buf.append(after)
            continue
        if active:
            if any(stop in stripped for stop in stops):
                break
            buf.append(stripped)
            if sum(len(x) for x in buf) >= max_chars:
                break
    return "\n".join(buf)[:max_chars]


def classify_goods(title: str, need: str) -> tuple[bool, str]:
    hay = f"{title} {need}"
    goods_hits = [k for k in GOODS_KEYWORDS if k in hay]
    service_hits = [k for k in SERVICE_ONLY_HINTS if k in hay]
    if goods_hits:
        return True, "goods_keyword:" + ",".join(goods_hits[:4])
    if service_hits:
        return False, "service_or_works:" + ",".join(service_hits[:4])
    return False, "goods_not_confirmed"


def parse_notice(url: str, html: str) -> dict[str, Any] | None:
    parser = parse_html(html)
    lines = [x for x in parser.lines if x]
    page_title = " ".join(parser.title_parts).strip()
    project_name = _field(lines, ("项目名称", "采购项目名称"))
    title = project_name or re.sub(r"[_-]中国政府采购网.*$", "", page_title).strip()
    buyer = _field(lines, ("采购单位", "采购人"))
    region = _field(lines, ("行政区域", "地域"), 60)
    budget = _field(lines, ("预算金额", "采购包预算金额", "最高限价"), 100)
    deadline = _field(lines, ("提交投标文件截止时间", "开标时间", "响应文件提交截止时间"), 120)
    method = _field(lines, ("采购方式",), 60)
    need = _section(
        lines,
        ("采购需求", "项目概况"),
        ("合同履行期限", "二、申请人的资格要求", "申请人的资格要求"),
    )
    eligibility = _section(
        lines,
        ("二、申请人的资格要求", "申请人的资格要求"),
        ("三、获取招标文件", "获取招标文件", "四、提交投标文件"),
        3500,
    )
    is_goods, reason = classify_goods(title, need)
    if not is_goods:
        return None

    excerpt = "\n".join(lines[:90])[:9000]
    return {
        "id": "ccgp:" + url.rsplit("/", 1)[-1].replace(".htm", ""),
        "source": "China Government Procurement Network (CCGP)",
        "source_type": "official_government_procurement",
        "source_url": url,
        "official_url": url,
        "official_links": [url],
        "title_original": title or page_title or "中国政府采购公告",
        "title_tr": "Çin kamu alımı — " + (title or page_title or "resmî ihale"),
        "detail_original": need or excerpt,
        "demand_summary_tr": "Resmî Çin kamu ihalesi. Orijinal talep metni Çince; ürün, teknik şartlar ve yabancı tedarikçi uygunluğu kaynak belge üzerinden incelenmelidir.",
        "buyer-name": buyer or "",
        "buyer-country": "CHINA",
        "country_name": "China",
        "market_region": "Çin / Doğu Asya",
        "regionname": region or "China",
        "product_name": title or "",
        "estimated_value": budget or "",
        "deadline": deadline or "",
        "procedure-type": method or "公开招标",
        "contract-nature": "goods",
        "opportunity_type": "china_public_procurement_goods",
        "translation_status": "pending_human_or_ai_translation",
        "market_access_status": "foreign_supplier_eligibility_review_required",
        "buyer_verified": False,
        "buyer_source_identified": bool(buyer),
        "china_goods_classification": reason,
        "technical-specification": need or "",
        "selection-criteria": eligibility or "",
        "supplier_research": {
            "status": "dossier_enrichment_pending",
            "product_query": title or "",
            "verified_count": 0,
        },
        "workflow": {
            "buyer": {"status": "source_identified_due_diligence_pending" if buyer else "identity_pending", "verified": False},
            "supplier": {"status": "research_pending", "verified_candidates": 0},
            "china_market_research": {
                "status": "public_procurement_demand_found",
                "product_query": title or "",
                "goal": "Yabancı tedarikçi uygunluğu, ithalat hacmi ve Çinli alıcı erişimi doğrulanacak",
            },
        },
        "source_excerpt": excerpt,
    }


def fetch_notice(url: str) -> dict[str, Any] | None:
    try:
        return parse_notice(url, fetch_html(url))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return None


def collect_china_opportunities(max_notices: int = 16) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    urls: list[str] = []
    errors: list[str] = []
    for index_url in INDEX_URLS:
        try:
            urls.extend(discover_notice_urls(fetch_html(index_url), index_url))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            errors.append(f"{index_url}: {type(exc).__name__}")
    urls = list(dict.fromkeys(urls))[: max_notices * 3]

    results: list[dict[str, Any]] = []
    if urls:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fetch_notice, url): url for url in urls}
            for future in as_completed(futures):
                item = future.result()
                if item:
                    results.append(item)
                    if len(results) >= max_notices:
                        break

    meta = {
        "source": "https://www.ccgp.gov.cn/",
        "status": "ok" if results else ("source_unavailable" if errors else "no_tradeable_goods_found"),
        "discovered_notice_urls": len(urls),
        "goods_opportunities_added": len(results),
        "errors": errors[:4],
        "foreign_supplier_eligibility_assumed": False,
    }
    return results, meta


def merge_payload(payload: dict[str, Any], max_notices: int = 16) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        opportunities = []
        payload["opportunities"] = opportunities
    china, meta = collect_china_opportunities(max_notices=max_notices)
    known = {str(o.get("id")) for o in opportunities if isinstance(o, dict) and o.get("id")}
    for item in china:
        if item["id"] not in known:
            opportunities.append(item)
            known.add(item["id"])
    payload["china_feed"] = meta
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m src.china_feed <json-file>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = merge_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = payload.get("china_feed") or {}
    print("CHINA_FEED " + json.dumps(meta, ensure_ascii=False, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    main()
