import unittest

from src.private_sync_payload import enrich_private_contact


class PrivateContactEvidenceTests(unittest.TestCase):
    def test_explicit_labelled_contact_fields_are_promoted(self):
        row = {
            "document_extracted_text": (
                "Contact Person: Jane Buyer\n"
                "Email: procurement@example.org\n"
                "Phone: +974 4400 1234\n"
                "Website: https://buyer.example.org/tenders"
            ),
            "source_url": "https://official.example.org/tender/42",
        }
        enrich_private_contact(row)
        self.assertEqual(row["contact_email"], "procurement@example.org")
        self.assertEqual(row["contact_phone"], "+974 4400 1234")
        self.assertEqual(row["contact_person"], "Jane Buyer")
        self.assertEqual(row["website"], "https://buyer.example.org/tenders")
        self.assertTrue(row["direct_contact_available"])
        self.assertTrue(row["contact_route_available"])
        self.assertTrue(row["contact_source_backed"])

    def test_unlabelled_email_and_phone_are_not_promoted(self):
        row = {
            "document_extracted_text": "procurement@example.org +974 4400 1234",
            "source_url": "https://official.example.org/tender/42",
        }
        enrich_private_contact(row)
        self.assertNotIn("contact_email", row)
        self.assertNotIn("contact_phone", row)
        self.assertFalse(row["direct_contact_available"])
        self.assertTrue(row["contact_route_available"])
        self.assertFalse(row["contact_source_backed"])

    def test_http_website_is_not_promoted_as_secure_contact_route(self):
        row = {"document_extracted_text": "Website: http://buyer.example.org"}
        enrich_private_contact(row)
        self.assertNotIn("website", row)
        self.assertFalse(row["direct_contact_available"])
        self.assertFalse(row["contact_route_available"])

    def test_existing_structured_contact_wins_over_document_candidate(self):
        row = {
            "contact_email": "structured@example.org",
            "document_extracted_text": "Email: document@example.org",
        }
        enrich_private_contact(row)
        self.assertEqual(row["contact_email"], "structured@example.org")


if __name__ == "__main__":
    unittest.main()
