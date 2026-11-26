"""Bounded official daily-package reader. No filesystem extraction or approval."""
from dataclasses import dataclass
import gzip
import hashlib
import io
from pathlib import PurePosixPath
import re
import tarfile
from xml.etree import ElementTree as ET

MAX_COMPRESSED = 32 * 1024 * 1024
MAX_EXPANDED = 256 * 1024 * 1024
MAX_MEMBERS = 12000
MAX_NOTICE = 2 * 1024 * 1024


def publication(value):
    match = re.fullmatch(r'([0-9]{1,8})-([0-9]{4})', str(value))
    if not match or int(match[1]) == 0:
        raise ValueError('invalid-publication')
    return f'{int(match[1])}-{match[2]}'


def daily_url(edition):
    match = re.fullmatch(r'([0-9]{1,3})/([0-9]{4})', str(edition))
    if not match or not 1 <= int(match[1]) <= 366:
        raise ValueError('invalid-ojs-edition')
    return f'https://ted.europa.eu/packages/daily/{match[2]}{int(match[1]):05d}'


def validate_notice(data, expected, edition):
    expected = publication(expected)
    daily_url(edition)
    if not 0 < len(data) <= MAX_NOTICE or re.search(br'<!\s*(?:DOCTYPE|ENTITY)', data, re.I):
        raise ValueError('invalid-bulk-notice-size-or-declaration')
    root = ET.fromstring(data)
    # This channel currently supports eForms, whose explicit publication metadata
    # can be checked independently of an attacker-controlled archive filename.
    fields = {}
    for node in root.iter():
        local = node.tag.rsplit('}', 1)[-1]
        if local in {'NoticePublicationID', 'GazetteID'}:
            fields.setdefault(local, set()).add((node.text or '').strip())
    ids = {publication(v) for v in fields.get('NoticePublicationID', set())}
    if ids != {expected} or fields.get('GazetteID') != {edition}:
        raise ValueError('bulk-notice-identity-mismatch')
    from src.ted_xml_parser import parse_ted_xml
    parse_ted_xml(data, f'https://ted.europa.eu/en/notice/{expected}/xml')


@dataclass(frozen=True)
class BulkNotice:
    publication: str
    edition: str
    data: bytes
    package_sha256: str

    def verified_payload(self, expected):
        if publication(expected) != self.publication:
            raise ValueError('bulk-notice-request-mismatch')
        validate_notice(self.data, expected, self.edition)
        if not re.fullmatch('[a-f0-9]{64}', self.package_sha256):
            raise ValueError('invalid-package-digest')
        # Keep the caller's valid zero padding in the evidence URL so the
        # existing exact requested-URL redirect check stays intact.
        return self.data, 'application/xml', f'https://ted.europa.eu/en/notice/{expected}/xml'


def select_daily_notices(compressed, edition, expected):
    """Pure parser: provenance of offline input is the caller's responsibility.

    Validate gzip CRC, bound expansion/members, never extract paths, and match
    both filename AND eForms publication/gazette metadata. No partial success.
    """
    daily_url(edition)
    wanted = {publication(v) for v in expected}
    if not 1 <= len(wanted) <= 10 or not 0 < len(compressed) <= MAX_COMPRESSED:
        raise ValueError('bulk-request-or-compressed-limit')
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        expanded = stream.read(MAX_EXPANDED + 1)
    if len(expanded) > MAX_EXPANDED:
        raise ValueError('bulk-expanded-limit')
    result = {}
    digest = hashlib.sha256(compressed).hexdigest()
    with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as archive:
        for count, member in enumerate(archive, 1):
            if count > MAX_MEMBERS:
                raise ValueError('bulk-member-limit')
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or '\\' in member.name or len(member.name) > 255:
                raise ValueError('unsafe-bulk-path')
            match = re.fullmatch(r'([0-9]{6}|[0-9]{8})_([0-9]{4})\.xml', path.name)
            if not match:
                continue
            identity = publication(f'{match[1]}-{match[2]}')
            if identity not in wanted:
                continue
            if not member.isfile() or member.size > MAX_NOTICE or identity in result:
                raise ValueError('invalid-or-duplicate-bulk-member')
            data = archive.extractfile(member).read(MAX_NOTICE + 1)
            if len(data) != member.size:
                raise ValueError('truncated-bulk-notice')
            validate_notice(data, identity, edition)
            result[identity] = BulkNotice(identity, edition, data, digest)
    if set(result) != wanted:
        raise ValueError('bulk-requested-notice-missing')
    return result


def fetch_daily_notices(edition, expected):
    """One documented official URL, using existing public-DNS/redirect guards."""
    from src.document_parser import _download
    url = daily_url(edition)
    data, content_type, final_url = _download(url, MAX_COMPRESSED)
    if final_url != url or not data.startswith(b'\x1f\x8b'):
        raise ValueError('bulk-source-not-official-gzip')
    return select_daily_notices(data, edition, expected)
