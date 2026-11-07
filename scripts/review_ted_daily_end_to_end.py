"""Single-shot official TED daily archive verification, no production writes.

Usage: python scripts/review_ted_daily_end_to_end.py YEAR OJS_ISSUE PUBLICATION OUTPUT_DIR
YEAR and OJS_ISSUE must be established from the official release calendar;
publication number is a different identifier. This tool does not infer the issue.
"""
import argparse
import json
from pathlib import Path

from fetch_ted_daily_package import fetch
from review_ted_daily_package import inspect


def run(year, issue, publication, output_dir):
    if not publication.endswith(f"-{year}"):
        raise ValueError("publication year does not match OJ S year")
    output_dir = Path(output_dir)
    archive = output_dir / f"ted-oj-s-{year}-{issue:03d}.tar.gz"
    acquisition = fetch(year, issue, archive)
    evidence = inspect(archive, publication)
    if evidence.get("publication_number") != publication or not evidence.get("notice_identity_verified") or not evidence.get("xml_parsed"):
        raise ValueError("notice identity or XML parse evidence missing")
    if evidence["package_sha256"] != acquisition["sha256"]:
        raise ValueError("archive hash mismatch between acquisition and inspection")
    result = {
        "oj_s_year": year, "oj_s_issue": issue, "publication_number": publication,
        "archive_sha256": acquisition["sha256"],
        "notice_xml_sha256": evidence["notice_xml_sha256"],
        "notice_xml_well_formed": evidence["xml_parsed"],
        "notice_identity_present_in_xml": evidence["notice_identity_verified"],
        "source_completeness_verified": False,
        "annexes_complete": False, "commercial_approval": False,
        "release_accepted": False,
    }
    # Preserve earlier evidence; reruns must use a new output directory.
    with (output_dir / "review-evidence.json").open("x", encoding="utf-8") as evidence_file:
        json.dump(result, evidence_file, indent=2)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int)
    parser.add_argument("issue", type=int)
    parser.add_argument("publication")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.year, args.issue, args.publication, args.output_dir), sort_keys=True))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Official TED daily review BLOCKED: {type(exc).__name__}: {exc}\n")
