"""Bounded batch fallback for notices the ordinary reader could not parse."""
from src.ted_bulk import daily_url, publication, fetch_daily_notices

MAX_EDITIONS = 2
MAX_NOTICES_PER_EDITION = 10


def apply_bulk_fallback(candidates, results, *, fetcher=None, enricher=None):
    if len(candidates) != len(results):
        raise ValueError('bulk-result-length-mismatch')
    if fetcher is None:
        fetcher = fetch_daily_notices
    if enricher is None:
        from src.ted_xml_enricher import enrich_opportunity
        enricher = enrich_opportunity
    report = {'edition_limit': MAX_EDITIONS, 'notice_limit_per_edition': MAX_NOTICES_PER_EDITION,
              'packages_attempted': 0, 'packages_failed': 0, 'notices_attempted': 0,
              'notices_recovered': 0, 'notices_skipped': 0}
    groups = {}
    for index, (row, success) in enumerate(zip(candidates, results)):
        if success:
            continue
        try:
            edition = row.get('ojs-number')
            if isinstance(edition, list) and len(edition) == 1:
                edition = edition[0]
            daily_url(edition)  # Only explicit, valid official metadata.
            identity = publication(row.get('publication-number'))
            if identity.rsplit('-', 1)[1] != edition.rsplit('/', 1)[1]:
                raise ValueError('publication-edition-year-mismatch')
        except (ValueError, TypeError):
            report['notices_skipped'] += 1
            continue
        if edition not in groups and len(groups) >= MAX_EDITIONS:
            report['notices_skipped'] += 1
            continue
        group = groups.setdefault(edition, {})
        if sum(len(indexes) for indexes in group.values()) >= MAX_NOTICES_PER_EDITION:
            report['notices_skipped'] += 1
            continue
        group.setdefault(identity, []).append(index)
    # One request per edition, serially, not once per opportunity or worker.
    for edition, identities in groups.items():
        report['packages_attempted'] += 1
        report['notices_attempted'] += sum(len(indexes) for indexes in identities.values())
        try:
            notices = fetcher(edition, list(identities))
            if set(notices) != set(identities):
                raise ValueError('incomplete-bulk-result')
            # Validate the entire selected set before mutating any row.
            for identity, notice in notices.items():
                notice.verified_payload(identity)
        except Exception:
            report['packages_failed'] += 1
            continue
        for identity, indexes in identities.items():
            for index in indexes:
                results[index] = enricher(candidates[index], bulk_notice=notices[identity])
                if results[index]:
                    report['notices_recovered'] += 1
    return report
