"""Read-only acceptance for an already downloaded *official* TED daily XML archive.

Important: A local archive alone is NOT proof of provenance. Caller must record the
official TED URL, raw response, and an independently verified digest separately.
Never sets annex/commercial acceptance flags and never contacts TED.
Usage: python -m src.ted_offline_archive_acceptance <file.tar.gz> <edition> <notice> [<notice>...]
"""
import hashlib
import json
from pathlib import Path
import sys

from src.ted_bulk import MAX_COMPRESSED, daily_url, publication, select_daily_notices


def inspect_archive(path, edition, notice_ids):
    official_url = daily_url(edition)
    notices = [publication(n) for n in notice_ids]
    if not 1 <= len(notices) <= 10 or len(set(notices)) != len(notices):
        raise ValueError('invalid-or-duplicate-requested-notices')
    file = Path(path)
    size = file.stat().st_size
    if not 0 < size <= MAX_COMPRESSED:
        raise ValueError('invalid-archive-size')
    compressed = file.read_bytes()
    selected = select_daily_notices(compressed, edition, notices)
    return {
        'archive_origin_verified': False,  # filesystem cannot authenticate the download
        'official_url_expected': official_url,
        'package_sha256': hashlib.sha256(compressed).hexdigest(),
        'archive_size_bytes': len(compressed),
        'notice_xml_validated': sorted(selected),
        'notice_only_acceptance': True,
        'linked_annexes_validated': False,
        'commercial_approval': False,
    }


def main():
    if len(sys.argv) < 4:
        raise SystemExit('usage: python -m src.ted_offline_archive_acceptance <archive.tar.gz> <S/YYYY> <notice> [notice...]')
    try:
        result = inspect_archive(sys.argv[1], sys.argv[2], sys.argv[3:])
    except (OSError, ValueError, TypeError, EOFError) as exc:
        print(json.dumps({'ok': False, 'error': type(exc).__name__, 'notice_only_acceptance': False,
                          'linked_annexes_validated': False, 'commercial_approval': False}), flush=True)
        raise SystemExit(1)
    print(json.dumps({'ok': True, **result}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
