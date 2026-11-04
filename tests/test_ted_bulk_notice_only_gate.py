"""Offline tests: official bulk notice metadata is NOT commercial or annex evidence."""
import unittest
from src.ted_bulk_probe import notice_only_acceptance


class BulkNoticeOnlyAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.valid = {'publication': '718662-2026', 'official_xml_parsed': True,
                      'text_chars': 3616, 'package_sha256': 'a' * 64,
                      'linked_documents_parsed': 0, 'commercial_approval': False}

    def test_valid_digest_and_notice_metadata_pass_only_notice_gate(self):
        self.assertTrue(notice_only_acceptance([self.valid]))

    def test_missing_or_invalid_digest_rejected(self):
        for digest in (None, '', 'abc', 'G' * 64):
            with self.subTest(digest=digest):
                self.assertFalse(notice_only_acceptance([{**self.valid, 'package_sha256': digest}]))

    def test_fail_closed_when_claims_or_evidence_incomplete(self):
        cases = [
            {**self.valid, 'commercial_approval': True},
            {**self.valid, 'commercial_approval': None},
            {**self.valid, 'official_xml_parsed': False},
            {**self.valid, 'text_chars': 0},
            {**self.valid, 'publication': '../718662-2026'},
            {**self.valid, 'publication': None},
            {},
        ]
        for item in cases:
            with self.subTest(item=item):
                self.assertFalse(notice_only_acceptance([item]))
        self.assertFalse(notice_only_acceptance([]))
        self.assertFalse(notice_only_acceptance(None))

    def test_boolean_text_count_is_not_a_real_document_length(self):
        self.assertFalse(notice_only_acceptance([{**self.valid, 'text_chars': True}]))

    def test_duplicate_publications_do_not_count_as_two_notices(self):
        self.assertFalse(notice_only_acceptance([self.valid, dict(self.valid)]))
        second = {**self.valid, 'publication': '718664-2026'}
        self.assertTrue(notice_only_acceptance([self.valid, second]))

    def test_one_invalid_notice_rejects_whole_batch(self):
        self.assertFalse(notice_only_acceptance([self.valid, {**self.valid, 'package_sha256': ''}]))


if __name__ == '__main__':
    unittest.main()
