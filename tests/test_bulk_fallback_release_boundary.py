"""Bulk TED recovery is source evidence, never attachment or trade approval."""
import unittest
from unittest.mock import patch
from src.ted_bulk import BulkNotice
from src.ted_xml_enricher import enrich_payload


class BulkFallbackReleaseBoundaryTests(unittest.TestCase):
    def test_bulk_xml_recovery_does_not_promote_source_or_commercial_approval(self):
        identity, edition = "123-2026", "197/2026"
        xml = (f"<ContractNotice><NoticePublicationID>{identity}</NoticePublicationID>"
               f"<GazetteID>{edition}</GazetteID><Description>"
               + "Tender description with source evidence only. " * 12
               + "</Description></ContractNotice>").encode()
        notice = BulkNotice(identity, edition, xml, "a" * 64)
        row = {"source": "TED", "publication-number": identity,
               "ojs-number": edition, "sourcing": False,
               "commercial_approval": False}
        payload = {"opportunities": [row]}
        def direct_or_bulk(item, *, bulk_notice=None):
            if bulk_notice is None:
                return False
            # Exercise the actual notice identity and source validation.
            bulk_notice.verified_payload(item["publication-number"])
            item["document_extraction"] = {
                "ted_xml_parsed": True, "parsed_count": 1,
                "attachment_candidates_omitted": 1,
                "document_versions_review_required": True,
                "attempts": [],
            }
            return True
        with patch("src.ted_xml_enricher.enrich_opportunity", side_effect=direct_or_bulk), \
             patch("src.ted_bulk_fallback.fetch_daily_notices",
                   return_value={identity: notice}) as fetch:
            result = enrich_payload(payload, bulk_enabled=True)
        fetch.assert_called_once_with(edition, [identity])
        self.assertEqual(result["document_extraction"]["ted_bulk_fallback"]["notices_recovered"], 1)
        self.assertEqual(result["document_extraction"]["ted_xml_parsed"], 1)
        self.assertFalse(row["sourcing"])
        self.assertFalse(row["commercial_approval"])
        self.assertTrue(row["document_extraction"]["document_versions_review_required"])
        self.assertEqual(row["document_extraction"]["attachment_candidates_omitted"], 1)

    def test_real_enricher_recovers_official_bulk_after_direct_waf(self):
        identity, edition = "123-2026", "197/2026"
        xml = (f"<ContractNotice><NoticePublicationID>{identity}</NoticePublicationID>"
               f"<GazetteID>{edition}</GazetteID><Description>"
               + "Verified official procurement source description. " * 12
               + "</Description></ContractNotice>").encode()
        notice = BulkNotice(identity, edition, xml, "a" * 64)
        row = {"source": "TED", "publication-number": identity,
               "ojs-number": edition, "sourcing": False, "commercial_approval": False}
        with patch("src.ted_xml_enricher._download_ted",
                   side_effect=ValueError("ted_waf_challenge")), \
             patch("src.ted_bulk_fallback.fetch_daily_notices",
                   return_value={identity: notice}):
            result = enrich_payload({"opportunities": [row]}, bulk_enabled=True)
        self.assertEqual(result["document_extraction"]["ted_bulk_fallback"]["notices_recovered"], 1)
        self.assertTrue(row["document_extraction"]["ted_xml_parsed"])
        self.assertFalse(row["sourcing"])
        self.assertFalse(row["commercial_approval"])

    def test_default_does_not_fetch_official_package(self):
        row = {"source": "TED", "publication-number": "123-2026",
               "ojs-number": "197/2026", "sourcing": False}
        with patch("src.ted_xml_enricher.enrich_opportunity", return_value=False), \
             patch("src.ted_bulk_fallback.fetch_daily_notices") as fetch:
            result = enrich_payload({"opportunities": [row]})
        fetch.assert_not_called()
        self.assertNotIn("ted_bulk_fallback", result["document_extraction"])


if __name__ == "__main__":
    unittest.main()
