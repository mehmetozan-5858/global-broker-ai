"""Deterministic attachment discovery hints, never evidence of suitability."""
from __future__ import annotations

import re
import urllib.parse

EXTENSIONS = ('.pdf', '.docx', '.txt')
TECHNICAL = re.compile(r'(?i)(?:\btechnical\b|\bspec(?:ification|ifications)?\b|\brequirements?\b|\bannex\b|\bleistungsverzeichnis\b|\blastenheft\b|\bspezifikation\b|\bspecyfikacja\b|\bswz\b|\bcctp\b|\bcahier\b|\bcapitolato\b|\btecnico\b|şartname|sartname|\bpliego\b|\bprescripciones\b|\bmemorial\s+descritivo\b|\btermo\s+de\s+refer[eê]ncia\b|\btechnische\s+specificaties\b|\bcaiet\s+de\s+sarcini\b)')
SUPPORTING = re.compile(r'(?i)(?:\bcriteri\b|\bevaluation criteria\b|\baward criteria\b)')
GENERAL = re.compile(r'(?i)\b(?:privacy|cookies?|gdpr|accessibility|datenschutz)\b')


def filename(url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
            return ''
        path = urllib.parse.unquote(parsed.path).rsplit('/', 1)[-1]
        if path.lower().endswith(EXTENSIONS):
            return path
        # E-ZAK's explicitly linked public download URLs encode the extension
        # as a final slug token. Display/login/redirect endpoints do not match.
        ezak = re.fullmatch(r'/document_[0-9]+/([a-f0-9]{32}-[a-z0-9_-]{1,240})-(pdf|docx|txt)',
                            urllib.parse.unquote(parsed.path), re.I)
        if ezak and parsed.scheme == 'https' and not parsed.query and not parsed.fragment:
            return ezak[1] + '.' + ezak[2].lower()
        for key, value in urllib.parse.parse_qsl(parsed.query, max_num_fields=30):
            if key.lower() in {'filename', 'file_name', 'download', 'file'} and not any(c in value for c in '/\\\x00\r\n') and value.lower().endswith(EXTENSIONS):
                return value
    except (TypeError, ValueError):
        pass
    return ''


def is_attachment_url(url: str) -> bool:
    return bool(filename(url))


def priority(url: str, label: str = '') -> int:
    hint = (filename(url) + ' ' + label).replace('_', ' ').replace('-', ' ')
    if TECHNICAL.search(hint) or re.search(r'\b(?:technick[aáéý]|specifikace)\b', hint, re.I):
        return 0
    if SUPPORTING.search(hint):
        return 1
    return 3 if GENERAL.search(hint) else 2


def select(candidates: list[tuple[str, str]], limit: int) -> list[str]:
    # Keep the strongest explicit label for duplicate links; tie order is stable.
    scores: dict[str, int] = {}
    for url, label in candidates:
        score = priority(url, label)
        scores[url] = min(scores.get(url, score), score)
    return sorted(scores, key=scores.get)[:limit]
