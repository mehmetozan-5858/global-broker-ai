import hashlib
import io
import unittest
import zipfile
from unittest.mock import patch
from src import document_links, document_parser


BASE = 'https://zakazky.krajbezkorupce.cz'
ANNEX = BASE + '/document_254114/70456a8a24715db566d2cb2f10172d37-priloha-c-5-zd-technicka-specifikace_27_10_2026-docx'


def docx(text):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:document>')
    return output.getvalue()


class EzakTests(unittest.TestCase):
    def test_narrow_slug_download_hints_exclude_pages_and_redirect_parameters(self):
        self.assertTrue(document_links.filename(ANNEX).endswith('.docx'))
        for bad in [ANNEX + '?redirect=x', ANNEX + '#x', ANNEX.replace('https:', 'http:'),
                    ANNEX.replace('document_254114', 'document_download_254114'),
                    ANNEX.replace('70456a8a24715db566d2cb2f10172d37', 'short'),
                    ANNEX.replace('-docx', '-zip')]:
            self.assertFalse(document_links.is_attachment_url(bad), bad)

    def test_realistic_source_discovery_retains_annex_and_byte_provenance(self):
        page = BASE + '/contract_display_47078.html'
        text = 'Technická specifikace: Objem nádrže minimálně 5000 litrů. ' * 5
        data = docx(text)
        body = ('<p>' + 'Tender context. ' * 20 + '</p>'
                + ''.join(f'<a href="/general{i}.pdf">General</a>' for i in range(3))
                + f'<a href="{ANNEX}">Příloha č. 5 Technická specifikace</a>').encode()
        def download(url, *args):
            if url == page: return body, 'text/html', page
            if url == ANNEX: return data, 'application/octet-stream', ANNEX
            raise OSError('fixture-unavailable')
        row = {'document_url': page}
        with patch.object(document_parser, '_download', side_effect=download):
            document_parser.enrich_opportunity(row)
        attempt = next(a for a in row['document_extraction']['attempts'] if a['url'] == ANNEX)
        self.assertEqual(attempt['status'], 'parsed')
        self.assertEqual(attempt['kind'], 'docx')
        self.assertEqual(attempt['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(attempt['discovered_from'], page)
        self.assertTrue(row['document_extracted_text'].startswith(text.strip()))
        self.assertNotIn('buyer_verified', row)

    def test_docx_oversized_xml_and_entity_declarations_are_rejected(self):
        with patch.object(document_parser, 'MAX_DOCUMENT_BYTES', 50):
            with self.assertRaisesRegex(ValueError, 'invalid_docx'):
                document_parser._parse_docx(docx('x' * 100))
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            archive.writestr('word/document.xml', '<!DOCTYPE x [<!ENTITY e "expanded">]><x>&e;</x>')
        with self.assertRaisesRegex(ValueError, 'invalid_docx'):
            document_parser._parse_docx(raw.getvalue())


if __name__ == '__main__': unittest.main()
