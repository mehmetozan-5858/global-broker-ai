import unittest
import json
import subprocess
import tempfile
from pathlib import Path

WORKFLOW=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"shadow-scan.yml").read_text(encoding="utf-8")

class ShadowScanPublishTests(unittest.TestCase):
    def test_actual_publication_steps_drop_private_data_and_pass_independent_gate(self):
        # Execute the workflow's real build and verification commands, without
        # invoking its scan, private ingest, queue, git push or Pages deployment.
        start = WORKFLOW.index('      - name: Build public-safe masked feed')
        stop = WORKFLOW.index('      - name: Commit masked Shadow Mode output', start)
        steps = WORKFLOW[start:stop].split('        run: |\n')[1:]
        row = {
            'source': 'TED', 'publication-number': '123456-2026',
            'title': 'Industrial machinery', 'quantity': '12 units',
            'export_goods_review': {'status': 'goods_candidate'},
            'new_private_analysis': {'unexpected': 'tel:+49123456'},
            'document_extracted_text': 'private document private@example.test',
            'specification_analysis': {'document_coverage_blockers': ['source_text_truncated']},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'data').mkdir()
            # Use the reviewed source module, but isolate all generated files.
            (root/'src').symlink_to(Path(__file__).resolve().parents[1]/'src', target_is_directory=True)
            private = {'opportunities': [row], 'new_private_summary': {'details': 'mailto:private@example.test'}}
            (root/'data/latest-opportunities.private.json').write_text(json.dumps(private))
            for section in steps:
                command = '\n'.join(line[10:] for line in section.splitlines() if line.startswith('          '))
                subprocess.run(['bash', '-eu', '-o', 'pipefail', '-c', command], cwd=root, check=True, capture_output=True)
            public = json.loads((root/'data/latest-opportunities.json').read_text())
            # A future projector regression must still be stopped by the
            # independent gate; a bare URI prefix was missed by the old scrub.
            poisoned = json.loads(json.dumps(public))
            poisoned['opportunities'][0]['product_detail'] = 'tel:'
            (root/'data/latest-opportunities.json').write_text(json.dumps(poisoned))
            with self.assertRaises(subprocess.CalledProcessError) as failure:
                subprocess.run(['bash', '-eu', '-o', 'pipefail', '-c', command], cwd=root, check=True, capture_output=True)
            self.assertIn(b'direct contact URI published in public feed', failure.exception.stderr)
        self.assertEqual(public['count'], 1)
        self.assertEqual(public['opportunities'][0]['product_name'], 'Industrial machinery')
        self.assertEqual(public['opportunities'][0]['document_coverage_blockers'], ['source_text_truncated'])
        self.assertNotIn('new_private_summary', public)
        self.assertNotIn('new_private_analysis', public['opportunities'][0])
        self.assertNotIn('private@example.test', json.dumps(public))

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
