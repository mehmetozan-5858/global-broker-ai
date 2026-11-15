"""Evaluate fixed offline holdout and count false acceptance separately from false rejection.

These metrics are for synthetic examples only; not a model quality estimate on real RFQs.
Exit nonzero when any unsafe positive verdict is found.
"""
from collections import Counter
from datetime import date
from evaluation_holdout_v9 import CASES
from proposal_v9 import verify_v9


def evaluate():
    counts = Counter()
    misses = []
    groups = {}
    for case in CASES:
        record = {"line": "L1", "company": "OUR_COMPANY", "region": "TR",
                  "text": case["text"]}
        if "verified" in case:
            record["verified"] = case["verified"]
        outcome = verify_v9(case["question"], [record], company="OUR_COMPANY",
                            region="TR", as_of=date(2026, 11, 15))
        actual, expected = outcome["decision"], case["expected"]
        counts["total"] += 1
        group = case["group"]
        groups.setdefault(group, Counter())["total"] += 1
        if actual == expected:
            counts["exact"] += 1
            groups[group]["exact"] += 1
        else:
            misses.append((case["id"], group, expected, actual))
        # A positive verdict absent positive gold evidence is the highest risk.
        if actual == "POSITIVE" and expected != "POSITIVE":
            counts["false_accept"] += 1
            groups[group]["false_accept"] += 1
        if expected == "POSITIVE" and actual != "POSITIVE":
            counts["false_reject"] += 1
            groups[group]["false_reject"] += 1
        if expected == "NEGATIVE" and actual == "REVIEW_SCOPE":
            counts["negative_abstention"] += 1
    return counts, groups, misses


if __name__ == "__main__":
    counts, groups, misses = evaluate()
    print("SYNTHETIC HOLDOUT — NOT REAL DOCUMENT ACCURACY")
    print("total={total} exact={exact} false_accept={false_accept} false_reject={false_reject} negative_abstention={negative_abstention}".format(
        **{key: counts[key] for key in ("total", "exact", "false_accept", "false_reject", "negative_abstention")}
    ))
    for group, metrics in sorted(groups.items()):
        print("group={} exact={}/{} unsafe_positive={}".format(
            group, metrics["exact"], metrics["total"], metrics["false_accept"]))
    for case_id, group, expected, actual in misses:
        print("MISMATCH {} [{}]: expected={} actual={}".format(case_id, group, expected, actual))
    if counts["false_accept"] > 0:
        raise SystemExit("NO-GO: one or more unsafe positive verdicts in synthetic holdout")
