import unittest
from pathlib import Path

WORKFLOW=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"shadow-scan.yml").read_text(encoding="utf-8")

class ShadowScanPublishTests(unittest.TestCase):
    def test_preserves_validated_data_across_main_updates(self):
        self.assertIn("git fetch origin main",WORKFLOW)
        self.assertIn("git reset --mixed origin/main",WORKFLOW)
        self.assertIn("git add data/latest-opportunities.json",WORKFLOW)
        self.assertIn("git push origin HEAD:main",WORKFLOW)
        self.assertNotIn("git pull --rebase origin main",WORKFLOW)
    def test_fails_closed_if_publish_cannot_finish(self):
        self.assertIn('if [ "$attempt" -eq 4 ]; then',WORKFLOW)
        self.assertIn("exit 1",WORKFLOW)

if __name__=="__main__":
    unittest.main()
