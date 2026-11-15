import unittest
from src.annex_review_summary import review_summary


class AnnexReviewQueueTests(unittest.TestCase):
    def test_queue_counts_without_disclosing_private_links_or_content(self):
        summary = review_summary({
            'attachment_candidates_observed': 3,
            'attachment_inventory_entries_omitted': 0,
            'text_truncated': True,
            'document_versions_review_required': True,
            'attachment_inventory': [
                {'kind': 'pdf', 'status': 'parsed', 'url': 'https://private.example/doc', 'text': 'PRIVATE'},
                {'kind': 'docx', 'status': 'skipped'},
                {'kind': 'xlsx', 'status': 'unsupported'},
            ],
        })
        self.assertTrue(summary['inventory_complete'])
        self.assertFalse(summary['all_observed_attachments_parsed'])
        self.assertTrue(summary['full_text_review_required'])
        self.assertTrue(summary['document_version_review_required'])
        self.assertNotIn('private.example', str(summary))
        self.assertNotIn('PRIVATE', str(summary))
        self.assertEqual(sum(row['count'] for row in summary['format_status_counts']), 3)

    def test_empty_partial_and_malformed_inventory_cannot_claim_completion(self):
        for info in ({}, {'attachment_candidates_observed': 0, 'attachment_inventory': []},
                     {'attachment_candidates_observed': 2, 'attachment_inventory_entries_omitted': 0, 'attachment_inventory': [{'kind': 'pdf', 'status': 'parsed'}]},
                     {'attachment_candidates_observed': 1, 'attachment_inventory_entries_omitted': 0, 'attachment_inventory': [{'kind': 'pdf', 'status': 'accepted'}]},
                     {'attachment_candidates_observed': True, 'attachment_inventory_entries_omitted': 0, 'attachment_inventory': [{'kind': 'pdf', 'status': 'parsed'}]}):
            with self.subTest(info=info):
                summary = review_summary(info)
                self.assertFalse(summary['inventory_complete'])
                self.assertFalse(summary['all_observed_attachments_parsed'])
                self.assertFalse(summary['commercial_approval'])


if __name__ == '__main__':
    unittest.main()
