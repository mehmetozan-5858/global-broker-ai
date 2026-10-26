import unittest
from unittest.mock import Mock, patch
from src.ted_bulk import BulkNotice
from src.ted_bulk_fallback import apply_bulk_fallback
from src.ted_xml_enricher import enrich_payload


def row(n, edition='197/2026'):
    return {'source':'TED', 'publication-number':f'{n}-2026', 'ojs-number':edition}


def notice(identity, edition):
    data=(f'<ContractNotice><NoticePublicationID>{identity}</NoticePublicationID>'
          f'<GazetteID>{edition}</GazetteID><Description>'+('Specification text. '*20)+
          '</Description></ContractNotice>').encode()
    return BulkNotice(identity, edition, data, 'a'*64)


class BatchFallbackTests(unittest.TestCase):
    def test_disabled_pipeline_does_not_fetch_packages(self):
        payload={'opportunities':[row(123)]}
        with patch('src.ted_xml_enricher.enrich_opportunity', return_value=False), \
             patch('src.ted_bulk_fallback.fetch_daily_notices') as fetch:
            enrich_payload(payload)
        fetch.assert_not_called()
        self.assertNotIn('ted_bulk_fallback', payload['document_extraction'])

    def test_one_package_for_shared_edition_and_duplicate_identity(self):
        rows=[row(123),row(124),row(123)];results=[False]*3
        fetch=Mock(side_effect=lambda ed,ids:{i:notice(i,ed) for i in ids})
        report=apply_bulk_fallback(rows,results,fetcher=fetch)
        fetch.assert_called_once_with('197/2026',['123-2026','124-2026'])
        self.assertEqual(results,[True]*3)
        self.assertEqual(report['notices_recovered'],3)
        self.assertTrue(all(r['document_extraction']['ted_xml_parsed'] for r in rows))
        self.assertTrue(all('buyer_verified' not in r for r in rows))

    def test_existing_success_invalid_metadata_and_missing_edition_are_not_downloaded(self):
        rows=[row(123),row(124,None),row(125,'1/2025'),row(126,'197/2026?redirect=x')]
        fetch=Mock();results=[True,False,False,False]
        report=apply_bulk_fallback(rows,results,fetcher=fetch)
        fetch.assert_not_called();self.assertEqual(report['notices_skipped'],3)

    def test_hard_batch_limits_include_duplicate_rows(self):
        rows=[row(123)]*12+[row(200+i,'198/2026') for i in range(11)]+[row(300,'199/2026')]
        results=[False]*len(rows)
        fetch=Mock(side_effect=lambda ed,ids:{i:notice(i,ed) for i in ids})
        report=apply_bulk_fallback(rows,results,fetcher=fetch)
        self.assertEqual(fetch.call_count,2)
        self.assertEqual(report['notices_attempted'],20)
        self.assertEqual(report['notices_skipped'],4)
        self.assertEqual(sum(results),20)

    def test_package_error_or_wrong_identity_does_not_partially_mutate_rows(self):
        for fetcher in (Mock(side_effect=ValueError('source failed')),
                        Mock(return_value={'123-2026':notice('123-2026','197/2026')}),
                        Mock(return_value={'123-2026':notice('999-2026','197/2026'),
                                           '124-2026':notice('124-2026','197/2026')})):
            rows=[row(123),row(124)];results=[False,False]
            report=apply_bulk_fallback(rows,results,fetcher=fetcher)
            self.assertEqual(report['packages_failed'],1)
            self.assertEqual(results,[False,False])
            self.assertTrue(all('document_extracted_text' not in r for r in rows))

    def test_enabled_existing_pipeline_recounts_actual_recovered_notices(self):
        payload={'opportunities':[row(123),row(124)]}
        def direct_or_bulk(item, *, bulk_notice=None):
            if bulk_notice is None:return False
            item['document_extraction']={'ted_xml_parsed':True,'parsed_count':1,'attempts':[]}
            return True
        with patch('src.ted_xml_enricher.enrich_opportunity', side_effect=direct_or_bulk), \
             patch('src.ted_bulk_fallback.fetch_daily_notices', side_effect=lambda ed,ids:{i:notice(i,ed) for i in ids}):
            enrich_payload(payload,bulk_enabled=True)
        summary=payload['document_extraction']
        self.assertEqual(summary['ted_xml_parsed'],2)
        self.assertEqual(summary['ted_document_failed_notices'],0)
        self.assertEqual(summary['ted_bulk_fallback']['packages_attempted'],1)
        self.assertEqual(summary['ted_bulk_fallback']['notices_recovered'],2)


if __name__ == '__main__':unittest.main()
