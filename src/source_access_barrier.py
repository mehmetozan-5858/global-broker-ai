"""Recognize observed public portal interstitials; never bypass or consent."""
from urllib.parse import urlsplit


def html_access_barrier(data, url):
    try:
        parsed=urlsplit(url)
        host=(parsed.hostname or '').lower()
        path=parsed.path.lower()
    except ValueError:
        return None
    text=data[:32768].decode('utf-8','replace').lower()
    if (host=='ekr.gov.hu' and len(data)<=8192 and
            'sajnáljuk' in text and 'karbantartást végzünk' in text):
        return 'source_portal_maintenance'
    if host=='cloud.3p.eu':
        if path=='/web/country.aspx' and 'btnbenl' in text and '__dopostback' in text:
            return 'source_country_selection_required'
        if path=='/web/information.aspx' and 'gebruiksvoorwaarden' in text:
            return 'source_terms_review_required'
    return None
