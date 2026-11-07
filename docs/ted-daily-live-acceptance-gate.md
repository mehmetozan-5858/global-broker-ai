# TED daily XML live-acceptance gate (review only)

CI evidence: Verified Brokerage CI #633, commit 2ca3ecf58e0fa22089fac7c1b6bfeb397466f4ff, completed success. This is offline test evidence, **not** an official TED archive fetch.

## Required evidence before acceptance

1. Obtain the **official OJ S issue number** for the target publication from TED metadata. A publication number such as 718662-2026 is **not** an OJ S issue number. Do not guess an issue from the publication date.
2. In a permitted, network-enabled isolated runner, execute once:
   `python scripts/review_ted_daily_end_to_end.py YEAR OJ_S_ISSUE PUBLICATION /tmp/ted-review`
3. Record the exact official URL, response status, final host, archive SHA256, extracted notice XML SHA256 and the process exit code. Never accept HTTP 202 / HTML / WAF responses as archives.
4. Confirm that the official archive's real structure and filename conventions match the parser. Offline fixture success does not prove compatibility with actual TED packages.
5. Validate structured publication identity and independently review source completeness, lot coverage, amendments, and all E-ZAK annexes. `source_completeness_verified`, `annexes_complete`, `commercial_approval`, and `release_accepted` must remain false until separately evidenced.
6. Only after a successful real fetch and human review may a separately approved change connect the verified package reader to production. No automatic workflow, merge, deploy, unpause, budget change, tender submission, or external write is authorized by this document.

## Failure handling

Any DNS/timeout/HTTP error, unexpected content, missing target notice, duplicate identity, archive safety violation, hash mismatch, or incomplete annex inventory is a **BLOCKED** result. Retain diagnostics without printing sensitive documents. Do not downgrade the source/identity gate or bypass anti-bot challenges.

## Known limitation

The current inspector supports bounded ZIP and TAR archives and a small set of expected XML member filenames. It has not yet been validated against an actual TED daily package. The CI #633 result must not be represented as a successful live TED acquisition.
