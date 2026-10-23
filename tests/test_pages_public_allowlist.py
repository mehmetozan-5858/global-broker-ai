"""GitHub Pages must reuse strict public field projection (not fragile denylist)."""
import unittest
from pathlib import Path
from src.public_opportunity_projection import project_public_opportunity

WORKFLOW = (Path(__file__).resolve().parents[1] / ".github/workflows/deploy-mobile.yml")


class PublicPagesProjectionTests(unittest.TestCase):
    def test_workflow_uses_allowlist_before_pages_upload(self):
        yaml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("from src.public_opportunity_projection import project_public_opportunity", yaml)
        self.assertIn("rows.append(project_public_opportunity(row))", yaml)
        self.assertNotIn("blocked_exact=", yaml)
        self.assertNotIn("rows.append(scrub(row))", yaml)
        self.assertIn("row.get('goods_status')!='goods_candidate'", yaml)
        self.assertLess(yaml.index("rows.append(project_public_opportunity(row))"),
                        yaml.index("actions/upload-pages-artifact@v3"))

    def test_reprojecting_masked_feed_discards_unknown_nested_private_fields(self):
        row = {
            "source": "TED", "title": "Industrial valve",
            "goods_status": "goods_candidate", "buyer_masked": True,
            "document_coverage_blockers": ["source_text_truncated"],
            "new_private_nested": {"contact": {"email": "secret@example.test"}},
            "supplier_research": {"candidates": [{"contact_email": "secret@example.test"}]},
        }
        result = project_public_opportunity(row)
        self.assertEqual(result["goods_status"], "goods_candidate")
        self.assertEqual(result["document_coverage_blockers"], ["source_text_truncated"])
        self.assertNotIn("secret@example.test", str(result))
        self.assertNotIn("new_private_nested", result)
        self.assertNotIn("supplier_research", result)


if __name__ == "__main__":
    unittest.main()
