import io
import unittest
import zipfile
from src.annex_review_audit import audit_bytes, spreadsheet


class BoundedAuditTests(unittest.TestCase):
    def test_spreadsheet_formula_is_read_as_source_not_evaluated(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            self.skipTest('openpyxl is installed by the dedicated audit job')
        workbook = Workbook()
        workbook.active['A1'] = 'Source quantity'
        workbook.active['B1'] = '=1+1'
        data = io.BytesIO()
        workbook.save(data)
        workbook.close()
        result = spreadsheet(data.getvalue())
        self.assertEqual(result['formula_cells'], 1)
        self.assertEqual(result['text_chars'], len('Source quantity') + len('=1+1'))
        self.assertFalse(result['text_truncated'])

    def test_fake_legacy_word_and_oversized_data_rejected(self):
        with self.assertRaisesRegex(ValueError, 'magic'):
            audit_bytes('doc', b'<html>not a Word file</html>', 'application/msword', 'https://example.test/doc')
        with self.assertRaisesRegex(ValueError, 'byte_limit'):
            audit_bytes('doc', b'x' * (8 * 1024 * 1024 + 1), 'application/msword', 'https://example.test/doc')

    def test_spreadsheet_entity_and_macro_members_rejected_before_loading(self):
        for name, body in [('xl/workbook.xml', b'<!DOCTYPE x [<!ENTITY y "boom">]><x/>'),
                           ('xl/vbaProject.bin', b'not executed')]:
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w') as archive:
                archive.writestr(name, body)
            with self.assertRaises(ValueError):
                spreadsheet(data.getvalue())


if __name__ == '__main__':
    unittest.main()
