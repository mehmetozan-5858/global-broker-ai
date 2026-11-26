import unittest
from src.ted_official_search_probe import search


class SearchProbeTests(unittest.TestCase):
    def test_exact_publication_only_is_metadata_not_document_acceptance(self):
        result=search("775258-2026",fetcher=lambda body:{
          "notices":[{"publication-number":"775259-2026"},
                     {"publication-number":"775258-2026"}]})
        self.assertEqual(result["matching_records"],1)
        self.assertTrue(result["metadata_match_only"])
        self.assertFalse(result["official_xml_bytes_verified"])
        self.assertFalse(result["annexes_verified"])
        self.assertFalse(result["commercial_acceptance"])

    def test_only_exact_official_xml_link_is_counted_as_advertised_not_verified(self):
        number="775258-2026"
        result=search(number,fetcher=lambda _:{"notices":[{
            "publication-number":number,
            "links":[
                "https://ted.europa.eu/en/notice/775258-2026/xml",
                "https://ted.europa.eu.evil.test/en/notice/775258-2026/xml",
                "https://ted.europa.eu/en/notice/999999-2026/xml"
            ]
        }]})
        self.assertEqual(result["official_xml_download_links_advertised"],1)
        self.assertFalse(result["official_xml_bytes_verified"])
        self.assertFalse(result["annexes_verified"])

    def test_mismatch_duplicate_and_timeout_fail_closed(self):
        self.assertEqual(search("775258-2026",fetcher=lambda _:{"notices":[{"publication-number":"775259-2026"}]})["matching_records"],0)
        with self.assertRaisesRegex(ValueError,"ted_search_duplicate_notice"):
            search("775258-2026",fetcher=lambda _:{"notices":[
                {"publication-number":"775258-2026"},
                {"publication-number":"775258-2026"}]})
        with self.assertRaisesRegex(ValueError,"ted_search_response_unverified"):
            search("775258-2026",fetcher=lambda _:{"notices":[],"timedOut":True})
        with self.assertRaises(ValueError):
            search("../other",fetcher=lambda _:self.fail("network should not run"))


if __name__=="__main__":
    unittest.main()
