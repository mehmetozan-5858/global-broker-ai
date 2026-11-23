import unittest
from src.private_source_host_gate import official_source_host, summarize_source_hosts, require_official_source_hosts, require_official_source_hosts


class PrivateSourceHostGateTests(unittest.TestCase):
    def test_exact_known_official_hosts(self):
        fixtures = {
            "TED": "https://ted.europa.eu/en/notice/-/detail/775258-2026",
            "WORLD_BANK": "https://projects.worldbank.org/en/projects-operations/project-detail/P000001",
            "SAM_GOV": "https://sam.gov/opp/example",
            "Qatar Monaqasat": "https://monaqasat.mof.gov.qa/tender/1",
            "Saudi Etimad official visitor API": "https://tenders.etimad.sa/Tender/Details/1",
        }
        for source, url in fixtures.items():
            with self.subTest(source=source):
                self.assertTrue(official_source_host(source, url))

    def test_lookalike_url_and_credentials_are_not_official(self):
        for url in [
            "http://ted.europa.eu/en/notice/123",
            "https://ted.europa.eu.evil.example/en/notice/123",
            "https://ted.europa.eu@evil.example/en/notice/123",
            "https://user@ted.europa.eu/en/notice/123",
            "https://ted.europa.eu:444/en/notice/123",
            "https://ted.europa.eu/",
            "//ted.europa.eu/en/notice/123",
            "https://ted.europa.eu\n/en/notice/123",
        ]:
            with self.subTest(url=url):
                self.assertFalse(official_source_host("TED", url))
        self.assertFalse(official_source_host("UNKNOWN", "https://ted.europa.eu/en/notice/123"))

    def test_aggregate_never_claims_content_or_party_verification(self):
        data = [
            {"source": "TED", "source_url": "https://ted.europa.eu/en/notice/123", "contact": "secret@example.test"},
            {"source": "TED", "source_url": "https://ted.europa.eu.bad.test/en/notice/123"},
            {"source": "WORLD_BANK", "source_url": "https://projects.worldbank.org/project/1"},
        ]
        report = summarize_source_hosts(data)
        self.assertEqual(report["rows"], 3)
        self.assertEqual(report["official_host_matches"], 2)
        self.assertEqual(report["official_host_mismatches"], 1)
        self.assertFalse(report["content_and_annex_verified"])
        self.assertFalse(report["commercial_party_verified"])
        self.assertNotIn("secret@example.test", str(report))


    def test_preflight_rejects_unofficial_host_even_with_unique_identity(self):
        valid={"source":"TED","source_url":"https://ted.europa.eu/en/notice/123",
               "opportunity_id":"synthetic-1"}
        self.assertEqual(require_official_source_hosts([valid])["official_host_matches"],1)
        bad={**valid,"source_url":"https://ted.europa.eu.attacker.test/en/notice/123"}
        with self.assertRaisesRegex(ValueError,"source_host_validation_blocked"):
            require_official_source_hosts([valid,bad])
        with self.assertRaises(ValueError):
            require_official_source_hosts([])


    def test_invalid_snapshot_fails_closed_without_echoing_input(self):
        for value in [None, {}, "private contact secret", 123]:
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaisesRegex(ValueError, "invalid_source_snapshot"):
                    require_official_source_hosts(value)

    def test_oversized_snapshot_fails_closed(self):
        rows = [{"source": "TED", "source_url": "https://ted.europa.eu/en/notice/123"}] * 1001
        with self.assertRaisesRegex(ValueError, "too_many_source_rows"):
            require_official_source_hosts(rows)


if __name__ == "__main__":
    unittest.main()
