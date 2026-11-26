"""Unit regressions: a green source-probe execution is not GB-02 acceptance."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_gb02_document_acceptance.py"
spec = importlib.util.spec_from_file_location("check_gb02_document_acceptance", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Gb02GateTests(unittest.TestCase):
    def test_green_diagnostic_with_no_linked_docs_is_blocked(self):
        log = '2026-11-23 TED_DOCUMENT_SOURCE_PROBE {"attempted":2,"parsed":1,"linked_documents_parsed":0,"linked_document_evidence_accepted":false,"annex_completeness_verified":false,"commercial_approval":false,"document_gate":"blocked_no_linked_document"}'
        self.assertFalse(module.inspect_log(log)["gb02_document_acceptance"])

    def test_one_parsed_document_is_not_complete_annex_acceptance(self):
        result = module.evaluate({"attempted":2,"linked_documents_parsed":1,
                                  "linked_document_evidence_accepted":True,
                                  "annex_completeness_verified":False,
                                  "commercial_approval":False,
                                  "document_gate":"review"})
        self.assertFalse(result["gb02_document_acceptance"])

    def test_missing_or_non_json_evidence_refused(self):
        with self.assertRaises(ValueError):
            module.inspect_log("CI success but no probe details")
        with self.assertRaises(Exception):
            module.inspect_log("TED_DOCUMENT_SOURCE_PROBE invalid JSON")

    def test_even_complete_document_gate_never_grants_commercial_approval(self):
        result = module.evaluate({"attempted":2,"linked_documents_parsed":10,
                                  "linked_document_evidence_accepted":True,
                                  "annex_completeness_verified":True,
                                  "commercial_approval":False,
                                  "document_gate":"accepted"})
        self.assertTrue(result["gb02_document_acceptance"])
        self.assertFalse(result["commercial_approval"])


    def test_string_and_boolean_counts_cannot_authorize_documents(self):
        sample = {"attempted": 2, "linked_documents_parsed": 1,
                  "linked_document_evidence_accepted": True,
                  "annex_completeness_verified": True,
                  "commercial_approval": False, "document_gate": "accepted"}
        for key, invalid in (("attempted", True),
                             ("attempted", "2"),
                             ("linked_documents_parsed", True),
                             ("linked_documents_parsed", "1"),
                             ("linked_documents_parsed", -1)):
            with self.subTest(key=key, invalid=invalid):
                self.assertFalse(module.evaluate({**sample, key: invalid})["gb02_document_acceptance"])


if __name__ == "__main__":
    unittest.main()
