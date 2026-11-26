"""Compare two private E-ZAK manifests without approving a procurement.

Exit 0 only when both inventories are complete, unchanged and error-free.
Exit 2 on any new, removed or changed source, or incomplete acquisition.
Usage: python scripts/ezak_manifest_diff.py previous.json current.json
"""
import argparse
import json
from pathlib import Path


def compare(previous, current):
    if previous.get("ezak_dbid") != current.get("ezak_dbid") or previous.get("source_index") != current.get("source_index"):
        raise ValueError("Source identity mismatch")
    def indexed(manifest):
        records = manifest.get("records")
        if not isinstance(records, list) or not records:
            raise ValueError("Missing document inventory")
        if any(not isinstance(item, dict) or item.get("error") or not item.get("source_url") or not item.get("sha256") for item in records):
            raise ValueError("Incomplete document inventory")
        urls = [item["source_url"] for item in records]
        if len(set(urls)) != len(urls):
            raise ValueError("Duplicate document source")
        return {item["source_url"]: item["sha256"] for item in records}
    before, after = indexed(previous), indexed(current)
    return {"added": sorted(set(after) - set(before)),
            "removed": sorted(set(before) - set(after)),
            "changed": sorted(url for url in set(before) & set(after) if before[url] != after[url]),
            "technical_approval": False, "commercial_approval": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    try:
        result = compare(json.loads(args.previous.read_text(encoding="utf-8")),
                         json.loads(args.current.read_text(encoding="utf-8")))
        print(json.dumps(result, ensure_ascii=False))
        if any(result[key] for key in ("added", "removed", "changed")):
            parser.exit(2, "Source revision requires review\n")
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Manifest review blocked: {type(exc).__name__}: {exc}\n")
