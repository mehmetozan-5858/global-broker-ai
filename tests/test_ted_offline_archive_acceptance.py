"""Offline source-chain acceptance: local bytes are never official provenance by themselves."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.ted_offline_archive_acceptance import inspect_archive


class OfflineArchiveAcceptanceTests(unittest.TestCase):
    def test_rejects_missing_or_empty_archive_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError):
                inspect_archive(Path(d)/'missing.gz', '215/2026', ['718662-2026'])
            empty=Path(d)/'empty.gz'
            empty.write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'invalid-archive-size'):
                inspect_archive(empty, '215/2026', ['718662-2026'])

    def test_rejects_invalid_edition_and_duplicate_notices(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'daily.gz'
            file.write_bytes(b'garbage')
            with self.assertRaises(ValueError):
                inspect_archive(file,'000/2026',['718662-2026'])
            with self.assertRaises(ValueError):
                inspect_archive(file,'215/2026',['718662-2026','718662-2026'])

    def test_structural_success_still_does_not_grant_official_or_commercial_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'daily.gz'
            file.write_bytes(b'fake-downloaded-bytes')
            with patch('src.ted_offline_archive_acceptance.select_daily_notices',
                       return_value={'718662-2026':object()}):
                result=inspect_archive(file,'215/2026',['718662-2026'])
            self.assertFalse(result['archive_origin_verified'])
            self.assertTrue(result['offline_notice_structure_validated'])
            self.assertFalse(result['notice_only_acceptance'])
            self.assertFalse(result['linked_annexes_validated'])
            self.assertFalse(result['commercial_approval'])
            self.assertEqual(result['official_url_expected'],
                             'https://ted.europa.eu/packages/daily/202600215')


if __name__=='__main__':
    unittest.main()
