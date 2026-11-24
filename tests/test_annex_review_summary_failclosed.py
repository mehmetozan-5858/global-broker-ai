import unittest
from src.annex_review_summary import review_summary


class AnnexReviewFailClosedTests(unittest.TestCase):
    def test_missing_or_empty_inventory_never_claims_complete(self):
        for item in ({}, {'attachment_candidates_observed': 0, 'attachment_inventory': [],
                        'attachment_inventory_entries_omitted': 0},
                     {'attachment_candidates_observed': 1, 'attachment_inventory': [],
                      'attachment_inventory_entries_omitted': 0}):
            with self.subTest(item=item):
                result = review_summary(item)
                self.assertFalse(result['inventory_complete'])
                self.assertFalse(result['all_observed_attachments_parsed'])
                self.assertFalse(result['commercial_approval'])

    def test_malformed_and_incomplete_inventory_fail_closed(self):
        cases = [
            {'attachment_candidates_observed': 1, 'attachment_inventory': [None],
             'attachment_inventory_entries_omitted': 0},
            {'attachment_candidates_observed': 1, 'attachment_inventory': [{'kind': 'unknown', 'status': 'parsed'}],
             'attachment_inventory_entries_omitted': 0},
            {'attachment_candidates_observed': 2, 'attachment_inventory': [{'kind': 'pdf', 'status': 'parsed'}],
             'attachment_inventory_entries_omitted': 1},
        ]
        for case in cases:
            with self.subTest(case=case):
                result = review_summary(case)
                self.assertFalse(result['inventory_complete'])
                self.assertFalse(result['all_observed_attachments_parsed'])
                self.assertFalse(result['commercial_approval'])

    def test_ambiguous_version_requires_review_even_when_inventory_complete(self):
        result = review_summary({
            'attachment_candidates_observed': 1,
            'attachment_inventory_entries_omitted': 0,
            'attachment_inventory': [{'kind': 'pdf', 'status': 'parsed'}],
        })
        self.assertTrue(result['inventory_complete'])
        self.assertTrue(result['document_version_review_required'])
        self.assertFalse(result['commercial_approval'])


if __name__ == '__main__':
    unittest.main()
