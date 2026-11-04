"""Offline tests: official bulk notice metadata is NOT commercial or annex evidence."""
import unittest
from src.ted_bulk_probe import notice_only_acceptance, summarize_attempt_evidence


class BulkNoticeOnlyAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.valid = {'publication': '718662-2026', 'official_xml_parsed': True,
                      'text_chars': 3616, 'source_channel': 'official_daily_xml_package', 'package_sha256': 'a' * 64,
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

    def test_unverified_source_channel_rejected(self):
        for channel in (None, '', 'ted_xml', 'linked_document', 'source_page'):
            with self.subTest(channel=channel):
                self.assertFalse(notice_only_acceptance([{**self.valid, 'source_channel': channel}]))

    def test_duplicate_publications_do_not_count_as_two_notices(self):
        self.assertFalse(notice_only_acceptance([self.valid, dict(self.valid)]))
        second = {**self.valid, 'publication': '718664-2026'}
        self.assertTrue(notice_only_acceptance([self.valid, second]))

    def test_bulk_and_linked_documents_are_independent(self):
        info = {'attempts': [
            {'status': 'parsed', 'source': 'ted_xml', 'source_channel': 'official_daily_xml_package',
             'source_package_sha256': 'a' * 64},
            {'status': 'parsed', 'source': 'linked_document'},
            {'status': 'parsed', 'source': 'attachment'},
            {'status': 'failed', 'source': 'linked_document'},
        ]}
        result = summarize_attempt_evidence(info)
        self.assertEqual(result['source_channel'], 'official_daily_xml_package')
        self.assertEqual(result['package_sha256'], 'a' * 64)
        self.assertEqual(result['linked_documents_parsed'], 2)

    def test_linked_documents_cannot_become_official_xml_digest(self):
        info = {'attempts': [
            {'status': 'parsed', 'source': 'linked_document',
             'source_package_sha256': 'b' * 64},
        ]}
        self.assertEqual(summarize_attempt_evidence(info), {
            'source_channel': None, 'package_sha256': None,
            'linked_documents_parsed': 1,
        })

    def test_imported_forged_bulk_provenance_is_not_current_evidence(self):
        forged = {'status': 'parsed', 'source': 'ted_xml',
                  'source_channel': 'official_daily_xml_package',
                  'source_package_sha256': 'b' * 64}
        direct = {'status': 'parsed', 'source': 'ted_xml'}
        info = {'attempts': [forged, direct]}
        evidence = summarize_attempt_evidence(info, new_attempt_offset=1)
        self.assertEqual(evidence['source_channel'], None)
        self.assertIsNone(evidence['package_sha256'])

    def test_new_bulk_attempt_after_cached_history_is_accepted(self):
        forged = {'status': 'parsed', 'source': 'ted_xml',
                  'source_channel': 'official_daily_xml_package',
                  'source_package_sha256': 'b' * 64}
        actual = {**forged, 'source_package_sha256': 'a' * 64}
        evidence = summarize_attempt_evidence(
            {'attempts': [forged, actual]}, new_attempt_offset=1)
        self.assertEqual(evidence['source_channel'], 'official_daily_xml_package')
        self.assertEqual(evidence['package_sha256'], 'a' * 64)

    def test_invalid_new_attempt_offsets_fail_closed(self):
        info = {'attempts': [{'status': 'parsed', 'source': 'ted_xml',
                              'source_channel': 'official_daily_xml_package',
                              'source_package_sha256': 'a' * 64}]}
        for offset in (-1, True, '0', None):
            with self.subTest(offset=offset):
                evidence = summarize_attempt_evidence(info, new_attempt_offset=offset)
                self.assertIsNone(evidence['package_sha256'])

    def test_malformed_attempt_metadata_fails_closed_without_crashing(self):
        for info in (None, {}, {'attempts': None}, {'attempts': 'parsed'},
                     {'attempts': {'status': 'parsed'}}, {'attempts': [None, 7, 'parsed']}):
            with self.subTest(info=info):
                self.assertEqual(summarize_attempt_evidence(info), {
                    'source_channel': None, 'package_sha256': None,
                    'linked_documents_parsed': 0,
                })

    def test_one_invalid_notice_rejects_whole_batch(self):
        self.assertFalse(notice_only_acceptance([self.valid, {**self.valid, 'package_sha256': ''}]))


if __name__ == '__main__':
    unittest.main()
