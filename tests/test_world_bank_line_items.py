import copy
import unittest
from src.world_bank_line_items import annotate, parse
from src.a5_source_terms import extract
from src.specification import analyze_opportunity
from src.public_opportunity_projection import project_public_opportunity

HEADER = "Lot No\nDescription\nQuantity\nPhysical Unit\nFinal (Project Site) Destination as specified in BDS\n"
TABLE = HEADER + "1: Northern Region\n10 mm2 Single Core Copper wire\n27,840\nMeter\nMzuzu\n2: Central Region\n10 mm2 Single Core Copper wire\n63,075\nMeter\nLilongwe\nThe Framework Agreement will not guarantee a call-off purchase."
URL = "https://search.worldbank.org/api/v2/procnotices?qterm=OP00000001&fl=id,notice_text"

class WorldBankLineItemTests(unittest.TestCase):
    def row(self):
        return {"id":"OP00000001","source":"WORLD_BANK","quantity":"unsafe aggregate",
                "public_source_terms":{"kind":"notice_estimate","estimated_budget":"50","budget_currency":"USD"}}

    def test_lots_quantities_units_and_destinations_remain_separate(self):
        rows = parse(TABLE)
        self.assertEqual(len(rows), 2)
        self.assertEqual([(r["lot_id"],r["quantity"],r["unit"],r["destination"]) for r in rows],
                         [("1","27840","m","Mzuzu"),("2","63075","m","Lilongwe")])

    def test_two_products_within_one_lot_do_not_become_one_quantity(self):
        table = HEADER + "1: Northern Region\n16mm2 Twine wire\n600,000\nMeter\nMzuzu\n10 mm2 Single Core Copper wire\n27,840\nMeter\nMzuzu\n"
        self.assertEqual(len(parse(table)), 2)

    def test_corrupt_quantity_or_unit_rejects_entire_table(self):
        for change in [TABLE.replace("63,075","63,07"),TABLE.replace("63,075","0"),
                       TABLE.replace("63,075","-1"),TABLE.replace("63,075","NaN"),
                       TABLE.replace("Meter","USD",1),TABLE.replace("Meter\nLilongwe","Meter")]:
            self.assertEqual(parse(change), [])

    def test_duplicate_products_reordered_or_empty_lots_are_not_guessed(self):
        duplicate = HEADER + "1: Northern Region\nPump\n25\nunits\nMzuzu\nPump\n30\nunits\nMzuzu\n"
        for table in [duplicate,TABLE.replace("2: Central","3: Central"),
                      HEADER + "1: Northern Region\nThe Framework Agreement applies.",
                      TABLE.replace("1: Northern Region","1: North\n2: Central Region")]:
            self.assertEqual(parse(table), [])

    def test_ambiguous_header_free_text_and_contact_like_cells_are_rejected(self):
        for table in [TABLE + TABLE, TABLE.replace("Physical Unit","Unknown"),
                      TABLE.replace("Mzuzu","private@example.invalid",1),
                      TABLE.replace("Mzuzu","Street 123",1), "Quantity: 25 units"]:
            self.assertEqual(parse(table), [])

    def test_exact_source_identity_is_required_and_prior_rows_are_cleared(self):
        for change,url in [({"source":"TED"},URL),({"id":"OP00000002"},URL),
                           ({},URL.replace("search.worldbank.org","example.invalid")),
                           ({},URL.replace("https:","http:"))]:
            row = self.row();row.update(change);row["source_line_items"]=[{"private":"old"}]
            self.assertEqual(annotate(row,TABLE,url),0)
            self.assertNotIn("source_line_items",row)

    def test_annotation_keeps_flat_scope_blocked_and_does_not_approve_price_or_spec(self):
        row=self.row();row.pop("quantity")
        self.assertEqual(annotate(row,TABLE,URL),2)
        row["document_extracted_text"]="Quantity: 25 units\nTechnical requirements: laboratory equipment ISO 9001 minimum capacity 500 units." * 3
        extract(row);analyze_opportunity(row)
        self.assertNotIn("quantity",row)
        self.assertFalse(row["specification_analysis"]["supplier_sourcing_ready"])
        self.assertNotIn("verified_unit_price",row)

    def test_public_projection_reports_counts_without_source_rows_or_flat_amounts(self):
        row=self.row();annotate(row,TABLE,URL)
        first=project_public_opportunity(row);second=project_public_opportunity(first)
        for out in (first,second):
            self.assertEqual(out["lot_count"],2)
            self.assertEqual(out["source_line_item_count"],2)
            self.assertTrue(out["lot_selection_required"])
            self.assertNotIn("approx_quantity",out)
            self.assertNotIn("estimated_budget",out)
            self.assertNotIn("source_line_items",out)
            self.assertNotIn("Mzuzu",str(out))
            self.assertNotIn("search.worldbank.org",str(out))

    def test_changed_source_clears_old_rows_instead_of_reusing_them(self):
        row=self.row();annotate(row,TABLE,URL)
        self.assertEqual(annotate(row,"No quantity table published",URL),0)
        self.assertNotIn("source_line_items_evidence",row)

    def test_real_source_layout_contains_twelve_rows_in_four_lots(self):
        groups=[("Northern Region","Mzuzu",["600,000","522,000","27,840"]),
                ("Central Region","Lilongwe",["1,400,000","1,218,000","63,075"]),
                ("Southern Region","Blantyre",["800,000","696,000","41,760"]),
                ("Eastern Region","Zomba",["600,000","522,000","27,840"])]
        text=HEADER
        for i,(label,destination,quantities) in enumerate(groups,1):
            text+=f"{i}: {label}\n"
            for product,quantity in zip(["16mm2 Twine wire","95mm Aerial Buddled Cable","10 mm2 Single Core Copper wire"],quantities):
                text+=f"{product}\n{quantity}\nMeter\n{destination}\n"
        text+="The Framework Agreement does not guarantee any purchase."
        rows=parse(text)
        self.assertEqual(len(rows),12)
        self.assertEqual(len({r["lot_id"] for r in rows}),4)
        self.assertEqual([r["quantity"] for r in rows if r["product"].startswith("10 mm2")],
                         ["27840","63075","41760","27840"])
