import json
import subprocess
import sys
import unittest


class LiveFeedDiagnosticsTests(unittest.TestCase):
    def test_print_document_failure_summary(self):
        proc = subprocess.run(
            [sys.executable, "-m", "src.feed_diagnostics", "data/latest-opportunities.json"],
            text=True,
            capture_output=True,
            check=True,
        )
        line = proc.stdout.strip()
        self.assertTrue(line.startswith("DOCUMENT_FEED_DIAGNOSTICS "))
        payload = json.loads(line.split(" ", 1)[1])
        print(line)
        self.assertGreaterEqual(payload["opportunities"], 1)


if __name__ == "__main__":
    unittest.main()
