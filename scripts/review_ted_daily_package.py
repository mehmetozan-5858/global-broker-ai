"""Review-only official TED daily XML package inspector (local archive, no network).

Official daily package URL pattern: https://ted.europa.eu/packages/daily/YYYYNNNNN
Download the archive through an authorized runner first. This tool neither
downloads nor approves notices; it checks archive safety and XML identity.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import zipfile
from xml.etree import ElementTree

MAX_ARCHIVE_BYTES = 80_000_000
MAX_XML_BYTES = 5_000_000
MAX_MEMBERS = 5000
MAX_EXPANDED_BYTES = 180_000_000


def inspect(archive_path, publication):
    if not re.fullmatch(r"[0-9]{1,8}-[0-9]{4}", publication):
        raise ValueError("invalid publication number")
    raw = Path(archive_path).read_bytes()
    if not raw or len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("archive size outside bounds")
    digest = hashlib.sha256(raw).hexdigest()
    number, year = publication.split("-")\n    # TED eForms uses eight-digit zero-padded publication numbers.\n    expected_names = {f"{int(number):08d}_{year}.xml", f"{int(number):06d}_{year}.xml"}
    matches = []
    total = 0

    def check_name(name, size):
        nonlocal total
        name = name.replace("\\", "/")
        parts = name.split("/")
        if name.startswith("/") or any(part in ("", ".", "..") for part in parts):
            raise ValueError("unsafe archive path")
        if size < 0 or size > MAX_XML_BYTES:
            raise ValueError("oversized member")
        total += size
        if total > MAX_EXPANDED_BYTES:
            raise ValueError("expanded archive exceeds limit")
        return parts[-1].lower() in expected_names

    def validate_xml(data):
        if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
            raise ValueError("XML DTD/entity forbidden")
        root = ElementTree.fromstring(data)
        if not isinstance(root.tag, str):
            raise ValueError("invalid XML root")
        # Filename alone cannot establish that the XML belongs to the notice.\n        if publication.encode("ascii") not in data:\n            raise ValueError("notice identity absent from XML content")\n        return hashlib.sha256(data).hexdigest()

    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            members = z.infolist()
            if len(members) > MAX_MEMBERS:
                raise ValueError("too many archive members")
            for member in members:
                if member.is_dir():
                    continue
                matched = check_name(member.filename, member.file_size)
                if matched:
                    with z.open(member) as f:
                        matches.append(validate_xml(f.read(MAX_XML_BYTES + 1)))
    elif tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as tar:
            members = tar.getmembers()
            if len(members) > MAX_MEMBERS:
                raise ValueError("too many archive members")
            for member in members:
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError("archive links/devices forbidden")
                matched = check_name(member.name, member.size)
                if matched:
                    f = tar.extractfile(member)
                    if f is None:
                        raise ValueError("unreadable archive member")
                    with f:
                        matches.append(validate_xml(f.read(MAX_XML_BYTES + 1)))
    else:
        raise ValueError("unsupported archive format")
    if len(matches) != 1:
        raise ValueError("target notice XML missing or duplicated")
    return {"source_channel": "official_daily_xml_package",
            "package_sha256": digest, "publication_number": publication,
            "notice_xml_sha256": matches[0], "xml_parsed": True,
            "notice_identity_verified": True, "source_completeness_verified": False,
            "annexes_complete": False, "commercial_approval": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("publication")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.archive, args.publication), sort_keys=True))
    except (ValueError, OSError, ElementTree.ParseError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(2, f"TED daily package review blocked: {type(error).__name__}: {error}\n")
