import unittest

from src.exportable_goods import classify


class ExportableGoodsTests(unittest.TestCase):
    def status(self, item):
        return classify(item)["status"]

    def test_goods(self):
        self.assertEqual(
            self.status({"title_original": "Supply and delivery of 25406 school desks", "procurement_category": "Goods"}),
            "goods_candidate",
        )

    def test_service_source_type_wins_even_if_material_word_exists(self):
        self.assertEqual(
            self.status({"title_original": "International materials engineer", "procurement_category": "Consulting Services"}),
            "exclude_service",
        )

    def test_works_source_type_wins_even_if_equipment_in_title(self):
        self.assertEqual(
            self.status({"title_original": "Construction works including equipment", "contract-nature": "works"}),
            "exclude_service",
        )

    def test_mixed(self):
        self.assertEqual(self.status({"title_original": "Supply of pumps and drilling services"}), "review_mixed")

    def test_unknown(self):
        self.assertEqual(self.status({"title_original": "Project development phase 2"}), "review_unknown")

    def test_goods_with_installation_requires_review(self):
        self.assertEqual(
            self.status({"title_original": "Supply of equipment with installation", "procurement_category": "Goods"}),
            "review_mixed",
        )

    def test_goods_with_engineering_requires_review(self):
        self.assertEqual(
            self.status({"title_original": "Supply of equipment and engineering services", "procurement_category": "Goods"}),
            "review_mixed",
        )

    def test_software_subscription_is_not_physical_goods(self):
        self.assertEqual(
            self.status({"title_original": "Enterprise software subscription and cloud services"}),
            "exclude_non_physical",
        )

    def test_hardware_and_support_is_mixed(self):
        self.assertEqual(
            self.status({"title_original": "Supply of servers with three years technical support"}),
            "review_mixed",
        )

    def test_goods_source_type_is_strong_evidence(self):
        decision = classify({"title_original": "Laboratory refrigerators", "procurement_category": "Goods"})
        self.assertEqual(decision["status"], "goods_candidate")
        self.assertEqual(decision["basis"], "source_goods_type")


if __name__ == "__main__":
    unittest.main()
