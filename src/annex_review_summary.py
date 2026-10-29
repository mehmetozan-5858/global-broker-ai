"""Read-only, privacy-safe explanation of the existing bounded annex sample.

This reports the normal reader's queue. It does not increase download limits,
select a document version, fetch unsupported formats or approve sourcing.
"""
from collections import Counter

from src.document_coverage import KNOWN


def review_summary(extraction):
    info = extraction if isinstance(extraction, dict) else {}
    inventory = info.get('attachment_inventory')
    inventory = inventory if isinstance(inventory, list) else []
    counts = Counter()
    invalid = 0
    for entry in inventory:
        if not isinstance(entry, dict):
            invalid += 1
            continue
        kind, status = entry.get('kind'), entry.get('status')
        if not isinstance(kind, str) or not isinstance(status, str) or kind not in KNOWN or status not in {'parsed', 'failed', 'skipped', 'unsupported'}:
            invalid += 1
            continue
        counts[kind, status] += 1
    observed = info.get('attachment_candidates_observed')
    consistent = type(observed) is int and observed > 0 and observed == len(inventory) and invalid == 0
    omitted = info.get('attachment_inventory_entries_omitted')
    complete_inventory = consistent and type(omitted) is int and omitted == 0
    return {
        'observed': observed if type(observed) is int and observed >= 0 else None,
        'inventory_entries': len(inventory),
        'inventory_complete': complete_inventory,
        'invalid_inventory_entries': invalid,
        'format_status_counts': [{'format': kind, 'status': status, 'count': count}
                                 for (kind, status), count in sorted(counts.items())],
        'all_observed_attachments_parsed': complete_inventory and all(status == 'parsed' for _, status in counts),
        'full_text_review_required': info.get('text_truncated') is True,
        'document_version_review_required': info.get('document_versions_review_required') is not False,
        'commercial_approval': False,
    }
