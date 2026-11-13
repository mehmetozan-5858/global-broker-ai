"""Pure offline-safe TED notice-only evidence gates; no imports of external providers."""

def notice_only_acceptance(outcomes):
    """Accept official notice metadata only; never infer linked-annex approval.

    The direct-document and technical-annex release gates remain independent.
    """
    import re
    if not isinstance(outcomes, list) or not outcomes:
        return False
    # A repeated publication must not count as two independently verified notices.
    identities = [item.get('publication') for item in outcomes if isinstance(item, dict)]
    if len(identities) != len(outcomes) or len(set(map(str, identities))) != len(identities):
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get('publication'), str)
        and bool(re.fullmatch(r'[1-9][0-9]{0,7}-[0-9]{4}', item['publication']))
        and item.get('official_xml_parsed') is True
        and item.get('source_channel') == 'official_daily_xml_package'
        and type(item.get('text_chars')) is int
        and item['text_chars'] > 0
        and isinstance(item.get('package_sha256'), str)
        and bool(re.fullmatch(r'[a-f0-9]{64}', item['package_sha256']))
        and item.get('commercial_approval') is False
        for item in outcomes
    )



def historic_attempt_offset(info):
    """Skip every imported history slot, including malformed non-dict entries."""
    attempts = info.get('attempts') if isinstance(info, dict) else None
    return len(attempts) if isinstance(attempts, list) else 0


def summarize_attempt_evidence(info, *, new_attempt_offset=0):
    """Use only newly executed attempts for official XML provenance.

    Search/cache metadata may contain forged historic attempt records.
    """
    attempts = info.get('attempts') if isinstance(info, dict) else None
    if type(new_attempt_offset) is not int or new_attempt_offset < 0:
        return {'source_channel': None, 'package_sha256': None, 'linked_documents_parsed': 0}
    valid = [a for a in attempts[new_attempt_offset:]
             if isinstance(a, dict) and a.get('status') == 'parsed'] if isinstance(attempts, list) else []
    bulk = [a for a in valid if a.get('source') == 'ted_xml'
            and a.get('source_channel') == 'official_daily_xml_package']
    return {
        'source_channel': 'official_daily_xml_package' if bulk else None,
        'package_sha256': next((a.get('source_package_sha256') for a in bulk if a.get('source_package_sha256')), None),
        'linked_documents_parsed': sum(a.get('source') in {'attachment', 'linked_document'} for a in valid),
    }


