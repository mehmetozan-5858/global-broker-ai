import io
import json
import unittest
from unittest.mock import patch
from src import broker
from src.ted_search_fields import apply_search_fields
from src.public_opportunity_projection import project_public_opportunity

def sample(**extra):
    return {"source":"TED", "publication-number":"123456-2026", "identifier-lot":["LOT-0001"],
            "estimated-value-lot":["120000"], "estimated-value-cur-lot":["EUR"], **extra}

class TedSearchFieldsTests(unittest.TestCase):
    def test_search_requests_documented_budget_currency_and_lot_identifiers(self):
        with patch.object(broker.urllib.request, "urlopen") as fetch:
            fetch.return_value.__enter__.return_value = io.BytesIO(b'{"notices":[]}')
            broker.ted_search("publication-date >= 20261001", 5)
            request = fetch.call_args.args[0]
            fields = json.loads(request.data)["fields"]
            self.assertTrue({"identifier-lot","estimated-value-lot","estimated-value-cur-lot"} <= set(fields))

    def test_single_lot_budget_is_source_estimate_not_supplier_price(self):
        row = apply_search_fields(sample())
        self.assertEqual(row["estimated_value"], "120000")
        self.assertEqual(row["budget_currency"], "EUR")
        self.assertFalse(row["structured_source_evidence"]["estimated_value"]["inferred"])
        self.assertNotIn("verified_unit_price", row)
        self.assertNotIn("buyer_verified", row)
        public = project_public_opportunity(row)
        self.assertEqual(public["estimated_budget"], "120000")
        self.assertEqual(public["budget_currency"], "EUR")
        self.assertNotIn("source_url", public)

    def test_multiple_lots_are_never_zipped_or_summed(self):
        for values in [["120000"], ["120000", "220000"]]:
            row = apply_search_fields(sample(**{"identifier-lot":["LOT-0001","LOT-0002"], "estimated-value-lot":values}))
            self.assertTrue(row["ted_lot_selection_required"])
            self.assertNotIn("estimated_value", row)
            self.assertNotIn("estimated_budget", project_public_opportunity(row))

    def test_ambiguous_amounts_and_currencies_remain_unpromoted(self):
        for fields in [{"estimated-value-lot":["12","20"]},{"estimated-value-cur-lot":["EUR","USD"]}]:
            self.assertNotIn("estimated_value", apply_search_fields(sample(**fields)))

    def test_missing_or_malformed_lot_scope_is_blocked(self):
        for ids in [[],["bad"],["LOT-0001","bad"]]:
            row=apply_search_fields(sample(**{"identifier-lot":ids}))
            self.assertNotIn("estimated_value",row)
            self.assertTrue(row["ted_lot_selection_required"])

    def test_invalid_values_do_not_become_budget_evidence(self):
        for amount in ["0","-1","NaN","Infinity",True,{},None]:
            self.assertNotIn("estimated_value",apply_search_fields(sample(**{"estimated-value-lot":amount})))

    def test_repeated_identical_single_lot_fields_are_deduplicated(self):
        row=apply_search_fields(sample(**{"identifier-lot":["LOT-0001","LOT-0001"],"estimated-value-lot":["120000","120000"]}))
        self.assertEqual(row["ted_lot_count"],1)
        self.assertEqual(row["estimated_value"],"120000")

    def test_conflicting_existing_budget_is_not_overwritten(self):
        row=apply_search_fields(sample(estimated_value="80",budget_currency="USD"))
        self.assertEqual(row["estimated_value"],"80")
        self.assertEqual(row["budget_currency"],"USD")

    def test_repeated_iso_date_z_is_normalized_without_concatenation(self):
        row=apply_search_fields(sample(**{"deadline-receipt-tender-date-lot":["2026-12-20Z","2026-12-20Z"]}))
        self.assertEqual(row["deadline-receipt-tender-date-lot"],"2026-12-20")
        row=apply_search_fields(sample(**{"deadline-receipt-tender-date-lot":["2026-12-20Z","2026-12-21Z"]}))
        self.assertIsInstance(row["deadline-receipt-tender-date-lot"],list)

    def test_wrong_source_or_publication_cannot_create_provenance(self):
        for fields in [{"source":"other"},{"publication-number":"../../x"}]:
            row=apply_search_fields(sample(**fields))
            self.assertNotIn("source_url",row)
            self.assertNotIn("estimated_value",row)

    def test_public_projection_checks_lot_and_notice_provenance(self):
        for key,value in [("ted_lot_count",2),("ted_search_lot_ids",["LOT-0002"]),("source","other")]:
            row=apply_search_fields(sample())
            row[key]=value
            self.assertNotIn("estimated_budget",project_public_opportunity(row))

if __name__=="__main__":
    unittest.main()
