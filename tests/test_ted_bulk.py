import gzip
import io
import tarfile
import unittest
from unittest.mock import patch
from src.ted_bulk import daily_url, select_daily_notices
from src.ted_xml_enricher import enrich_opportunity


def xml(identity='00000123-2026', edition='197/2026'):
    return ('<ContractNotice><NoticePublicationID>'+identity+'</NoticePublicationID>'
            '<GazetteID>'+edition+'</GazetteID><Description>'+('Technical procurement notice. '*15)+
            '</Description></ContractNotice>').encode()


def package(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as archive:
        for name, data, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    return output.getvalue()


class BulkTests(unittest.TestCase):
    def test_documented_url_and_strict_inputs(self):
        self.assertEqual(daily_url('197/2026'), 'https://ted.europa.eu/packages/daily/202600197')
        for edition in ('0/2026', '197/2026?url=x', '../2026', '367/2026'):
            with self.assertRaises(ValueError): daily_url(edition)

    def test_checked_notice_enters_existing_reader_without_direct_notice_fetch(self):
        data = package([('20261012_197/00000123_2026.xml', xml(), tarfile.REGTYPE)])
        notice = select_daily_notices(data, '197/2026', ['123-2026'])['123-2026']
        item = {'source':'TED', 'publication-number':'123-2026'}
        with patch('src.document_parser._download', side_effect=AssertionError('no-direct-fetch')):
            self.assertTrue(enrich_opportunity(item, bulk_notice=notice))
        self.assertTrue(item['document_extraction']['ted_xml_parsed'])
        self.assertEqual(item['document_extraction']['attempts'][-1]['source_package_sha256'], notice.package_sha256)
        self.assertNotIn('buyer_verified', item)
        padded = {'source':'TED', 'publication-number':'00000123-2026'}
        with patch('src.document_parser._download', side_effect=AssertionError('no-direct-fetch')):
            self.assertTrue(enrich_opportunity(padded, bulk_notice=notice))
        other = {'source':'TED', 'publication-number':'999-2026'}
        with patch('src.document_parser._download', side_effect=AssertionError('no-fallback')):
            self.assertFalse(enrich_opportunity(other, bulk_notice=notice))

    def test_filename_cannot_override_embedded_identity_or_edition(self):
        for content in (xml('124-2026'), xml(edition='198/2026')):
            with self.assertRaisesRegex(ValueError, 'identity-mismatch'):
                select_daily_notices(package([('00000123_2026.xml', content, tarfile.REGTYPE)]), '197/2026', ['123-2026'])

    def test_unsafe_paths_symlinks_and_duplicate_target_are_rejected(self):
        entry = ('00000123_2026.xml', xml(), tarfile.REGTYPE)
        for entries in ([('../00000123_2026.xml', xml(), tarfile.REGTYPE)],
                        [('00000123_2026.xml', b'', tarfile.SYMTYPE)], [entry, entry]):
            with self.assertRaises(ValueError): select_daily_notices(package(entries), '197/2026', ['123-2026'])

    def test_expansion_member_and_notice_limits(self):
        data = package([('00000123_2026.xml', xml(), tarfile.REGTYPE)])
        for key in ('MAX_EXPANDED', 'MAX_MEMBERS', 'MAX_NOTICE', 'MAX_COMPRESSED'):
            with self.subTest(key=key), patch('src.ted_bulk.'+key, 0 if key == 'MAX_MEMBERS' else 1), self.assertRaises(ValueError):
                select_daily_notices(data, '197/2026', ['123-2026'])

    def test_missing_notice_gzip_corruption_and_declarations_fail_closed(self):
        data = package([('00000123_2026.xml', xml(), tarfile.REGTYPE)])
        with self.assertRaises(ValueError): select_daily_notices(data, '197/2026', ['123-2026', '124-2026'])
        broken = bytearray(data);broken[-8] ^= 255
        with self.assertRaises((OSError, EOFError)): select_daily_notices(bytes(broken), '197/2026', ['123-2026'])
        declaration = b'<!DOCTYPE ContractNotice [<!ENTITY x "bad">]>'+xml()
        with self.assertRaises(ValueError):
            select_daily_notices(package([('00000123_2026.xml', declaration, tarfile.REGTYPE)]), '197/2026', ['123-2026'])


if __name__ == '__main__': unittest.main()
