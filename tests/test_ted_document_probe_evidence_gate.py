"""Ensure the live TED document probe never confuses reachability with evidence acceptance."""
from pathlib import Path
import unittest

class TedDocumentProbeEvidenceGateTests(unittest.TestCase):
    def test_live_probe_has_explicit_document_evidence_fail_closed_fields(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "ted_document_probe.py").read_text(encoding="utf-8")
        self.assertIn("'linked_document_evidence_accepted': linked>0", source)
        self.assertIn("'annex_completeness_verified': False", source)
        self.assertIn("'commercial_approval': False", source)
        self.assertIn("'blocked_no_linked_document'", source)

if __name__ == "__main__":
    unittest.main()
