# Source document freshness

Document extraction refetches every current source page and document on every scan, including when the notice ID and URL have not changed. This detects amendments published at the same address.

Each extraction records `checked_at` (UTC) and `refresh_policy: every_scan`. This timestamp records our read attempt, not the publisher revision date or a guarantee of source completeness. The existing scheduled scan is every six hours; scans can also be triggered by code changes or manually.

Previous extracted text is never reused as active evidence. A failed read records a failed attempt and clears old document text; a removed source cannot retain old document evidence. Other independently supplied structured fields are unchanged. Successful earlier scans remain in repository history, but are not substituted for current document reads.

The optional previous-payload CLI argument remains accepted for compatibility. `reused_last_known_good` is always zero. Network limits, timeouts, SSRF restrictions and attachment limits are unchanged.

Validation: 514 Python tests passed locally, including same-address quantity amendments, failed refresh, and removed-source regression cases. No synthetic customer or supplier records are persisted. This is a freshness fix, not acceptance of a complete commercial dossier, and does not change weighted delivery percentages.
