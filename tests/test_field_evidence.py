import unittest
from src.field_evidence import annotate, process_payload


class FieldEvidenceTests(unittest.TestCase):
    def test_source_fields_are_recorded_with_provenance(self):
        item={
            "buyer-country":"DEU",
            "place-of-performance-city-lot":"Berlin",
            "title_original":"Supply of 500 industrial pumps",
            "quantity-lot":"500 units",
            "deadline-receipt-tender-date-lot":"2026-11-12",
            "buyer-name":"Example Public Buyer",
        }
        annotate(item)
        self.assertEqual(item["field_evidence"]["country"]["value"],"DEU")
        self.assertEqual(item["field_evidence"]["country"]["source_field"],"buyer-country")
        self.assertEqual(item["field_evidence"]["quantity"]["value"],"500 units")
        self.assertEqual(item["field_evidence"]["quantity"]["status"],"source_backed")
        self.assertTrue(item["core_field_coverage"]["complete"])

    def test_missing_city_and_quantity_stay_missing(self):
        item={
            "title_original":"Saudi Arabia - supply 1000 chairs to Riyadh",
            "buyer-country":"SAU",
            "buyer-name":"Buyer",
            "deadline":"2026-12-01",
        }
        annotate(item)
        self.assertEqual(item["field_evidence"]["city"]["status"],"missing")
        self.assertIsNone(item["field_evidence"]["city"]["value"])
        self.assertEqual(item["field_evidence"]["quantity"]["status"],"missing")
        self.assertIsNone(item["field_evidence"]["quantity"]["value"])
        self.assertIn("city",item["missing_core_fields"])
        self.assertIn("quantity",item["missing_core_fields"])

    def test_source_title_can_back_product_but_not_other_fields(self):
        item={"title_original":"Supply of laboratory freezers"}
        annotate(item)
        self.assertEqual(item["field_evidence"]["product"]["status"],"source_backed")
        self.assertEqual(item["field_evidence"]["product"]["source_field"],"title_original")
        self.assertEqual(item["field_evidence"]["country"]["status"],"missing")
        self.assertEqual(item["field_evidence"]["buyer"]["status"],"missing")

    def test_payload_summary_counts_only_source_backed_values(self):
        data={"opportunities":[
            {"title_original":"Supply of desks","buyer-country":"FRA","quantity":"200"},
            {"title_original":"Supply of pumps","buyer-country":"DEU"},
        ]}
        process_payload(data)
        summary=data["field_evidence_summary"]
        self.assertEqual(summary["opportunities"],2)
        self.assertEqual(summary["source_backed_counts"]["country"],2)
        self.assertEqual(summary["source_backed_counts"]["quantity"],1)
        self.assertEqual(summary["complete_core_records"],0)
        self.assertIn("no inferred value",summary["rule"])


if __name__=="__main__":
    unittest.main()
