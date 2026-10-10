import unittest
from pathlib import Path

WORKFLOW=(Path(__file__).resolve().parents[1]/".github/workflows/shadow-scan.yml").read_text(encoding="utf-8")

class ScanRuntimeGuardrailTests(unittest.TestCase):
    def test_serialized_and_bounded(self):
        self.assertIn("group: global-broker-shadow-scan",WORKFLOW)
        self.assertIn("cancel-in-progress: false",WORKFLOW)
        self.assertIn("timeout-minutes: 55",WORKFLOW)
        for name in ("broker","china_feed","china_ggzy_feed","china_import_radar","document_parser","ted_xml_enricher","verification"):
            self.assertIn("scan_step "+name+" ",WORKFLOW)

    def test_core_broker_does_not_block_on_per_notice_translation(self):
        self.assertIn("b.auto_translate_tr=lambda text:\"\"",WORKFLOW)
        self.assertIn("scan_step broker 180",WORKFLOW)
        self.assertNotIn('scan_step broker 360 python src/broker.py',WORKFLOW)

    def test_atomic_feed_and_diagnostics(self):
        self.assertIn('echo "SCAN_STEP_OK $label duration=$((SECONDS-started))s" >&2',WORKFLOW)
        self.assertIn('mv "$NEXT" data/latest-opportunities.private.json',WORKFLOW)
        self.assertIn("Prepare private opportunity identities",WORKFLOW)
        self.assertIn("Sync full opportunities to private Supabase storage",WORKFLOW)
        self.assertIn("Build public-safe masked feed",WORKFLOW)
        self.assertIn("PUBLIC_FEED_PRIVACY_GATE_OK",WORKFLOW)
        self.assertIn('refusing to replace live data',WORKFLOW)

if __name__=="__main__":
    unittest.main()
