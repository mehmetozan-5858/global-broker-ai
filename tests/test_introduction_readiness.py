"""Regression tests for introduction readiness, without network calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.introduction_readiness import introduction_preflight, missing_dossier_fields
from src.public_opportunity_projection import project_public_opportunity


class IntroductionReadinessTests(unittest.TestCase):
    def test_generic_product_and_missing_fields_are_rejected(self):
        item = {"product_name": "Medikal ürün alımı", "country": "Poland", "source_type": "TED"}
        self.assertIn("product_name", missing_dossier_fields(item))
        self.assertIn("approx_quantity", missing_dossier_fields(item))
        self.assertIn("deadline", missing_dossier_fields(item))

    def test_specific_product_with_basic_fields_passes(self):
        item = {
            "product_name": "12V 100Ah starter battery",
            "country": "Poland",
            "approx_quantity": "500 units",
            "deadline": "2026-12-31",
            "source_name": "Official tender portal",
        }
        self.assertEqual([], missing_dossier_fields(item))

    def test_newly_ingested_opportunity_is_always_classified(self):
        # A new opportunity outside the original feed gets the same checks.
        new_row = {
            "id": "future-2027-001",
            "title": "Araç parçası",
            "country": "Germany",
            "source_type": "TED",
            "export_goods_review": {"status": "goods_candidate"},
        }
        projected = project_public_opportunity(new_row)
        self.assertEqual("research_required", projected["dossier_status"])
        self.assertIn("product_name", projected["missing_dossier_fields"])
        self.assertIn("approx_quantity", projected["missing_dossier_fields"])
        self.assertIn("deadline", projected["missing_dossier_fields"])

    def test_missing_feed_fails_closed(self):
        with patch("src.introduction_readiness._feed_path", return_value=None):
            self.assertEqual((503, "OPPORTUNITY_FEED_UNAVAILABLE"), introduction_preflight("anything"))

    def test_incomplete_matching_row_rejected_before_credit_rpc(self):
        row = {
            "title": "Medikal ürün alımı",
            "country": "Poland",
            "source_type": "TED",
            "export_goods_review": {"status": "goods_candidate"},
        }
        with tempfile.TemporaryDirectory() as directory:
            feed = Path(directory) / "feed.json"
            feed.write_text(json.dumps({"opportunities": [row]}), encoding="utf-8")
            with patch("src.introduction_readiness._feed_path", return_value=feed):
                with patch("src.introduction_readiness.project_public_opportunity", return_value={
                    "opportunity_id": "known-id", "product_name": "Medikal ürün alımı",
                    "country": "Poland", "source_type": "TED",
                }):
                    self.assertEqual(
                        (409, "OPPORTUNITY_DOSSIER_INCOMPLETE"),
                        introduction_preflight("known-id"),
                    )
                    self.assertEqual(
                        (404, "OPPORTUNITY_NOT_FOUND"),
                        introduction_preflight("unknown-id"),
                    )


if __name__ == "__main__":
    unittest.main()
