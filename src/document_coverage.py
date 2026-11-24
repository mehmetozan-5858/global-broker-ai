"""Private inventory of observed links, never a claim of complete tender scope."""
import re
import unicodedata
from urllib.parse import urljoin, urlsplit, unquote
from src.document_links import filename

SUPPORTED = {'pdf', 'docx', 'txt'}
KNOWN = SUPPORTED | {'doc', 'xls', 'xlsx', 'zip'}


def attachment_name(url):
    try:
        p = urlsplit(url)
        if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password:
            return ''
        name = filename(url)
        if name:
            return name
        path = unquote(p.path)
        name = path.rsplit('/', 1)[-1]
        if name.rsplit('.', 1)[-1].lower() in KNOWN and '.' in name:
            return name
        match = re.fullmatch(r'/document_[0-9]+/([a-f0-9]{32}-[a-z0-9_-]{1,240})-(doc|xls|xlsx|zip)', path, re.I)
        if match and p.scheme == 'https' and not p.query and not p.fragment:
            return match[1] + '.' + match[2].lower()
    except (TypeError, ValueError):
        pass
    return ''


def observe(links, base_url, inventory):
    for link in links:
        try:
            url = urljoin(base_url, link['href'])
            name = attachment_name(url)
            if not name:
                continue
            inventory.setdefault(url, {'url': url, 'kind': name.rsplit('.', 1)[-1].lower(),
                                       'discovered_from': base_url})
        except (KeyError, TypeError, ValueError):
            continue


def version_family(url):
    name = attachment_name(url)
    if not name:
        return None
    stem, ext = name.rsplit('.', 1)
    stem = re.sub(r'^[a-f0-9]{32}-', '', stem, flags=re.I)
    stem = unicodedata.normalize('NFKD', stem).encode('ascii', 'ignore').decode().lower()
    stem = re.sub(r'[^a-z0-9]+', '_', stem).strip('_')
    # A date suffix is only a possible revision hint. Never choose a winner.
    dated = bool(re.search(r'_(?:[0-3]?[0-9])_(?:[01]?[0-9])_(?:20[0-9]{2})$', stem))
    stem = re.sub(r'_(?:[0-3]?[0-9])_(?:[01]?[0-9])_(?:20[0-9]{2})$', '', stem)
    if dated:
        stem = re.sub(r'_(?:aktualni_zneni|aktualni)$', '', stem)
    p = urlsplit(url)
    return (p.scheme, p.netloc.lower(), stem, ext.lower()), dated


def summarize(inventory, attempts):
    by_url = {a.get('url'): a for a in attempts if isinstance(a, dict) and a.get('source') in {'attachment', 'linked_document'}}
    entries, families = [], {}
    for url, candidate in inventory.items():
        attempt = by_url.get(url, {})
        state = ('parsed' if attempt.get('status') == 'parsed' else
                 'failed' if attempt else 'unsupported' if candidate['kind'] not in SUPPORTED else 'skipped')
        entry = dict(candidate, status=state)
        if state == 'parsed' and attempt.get('sha256'):
            entry['sha256'] = attempt['sha256']
        entries.append(entry)
        family = version_family(url)
        if family:
            key, dated = family
            families.setdefault(key, []).append((url, dated))
    groups = [{'urls': [u for u, _ in values], 'resolution': 'review_required'}
              for values in families.values() if len(values) > 1 and any(d for _, d in values)]
    return {'attachment_candidates_observed': len(entries),
            'attachment_candidates_omitted': sum(e['status'] in {'unsupported', 'skipped'} for e in entries),
            'attachment_candidates_unsupported': sum(e['status'] == 'unsupported' for e in entries),
            'attachment_candidates_failed': sum(e['status'] == 'failed' for e in entries),
            'attachment_inventory': entries[:100], 'attachment_inventory_entries_omitted': max(0, len(entries) - 100),
            'document_versions_review_required': bool(groups), 'document_version_groups': groups[:100]}
