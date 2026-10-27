import unittest
from src.document_parser import _parse_html_page
from src.source_access_barrier import html_access_barrier


class BarrierTests(unittest.TestCase):
    def test_observed_portal_pages_cannot_become_notice_text_or_attachments(self):
        cases=[('https://ekr.gov.hu/eljarastar/eljaras/EKR001898952026',
                '<html>Sajnáljuk, a rendszeren karbantartást végzünk....</html>','source_portal_maintenance'),
               ('https://cloud.3p.eu/Web/Country.aspx',
                '<html>btnBENL __doPostBack <a href="privacy.pdf">privacy</a></html>','source_country_selection_required'),
               ('https://cloud.3p.eu/Web/Information.aspx',
                '<html>checkInfo Ik wens mij niet te identificeren <a href="terms.pdf">terms</a></html>','source_anonymous_choice_required')]
        for url,html,reason in cases:
            with self.subTest(reason=reason),self.assertRaisesRegex(ValueError,reason):
                _parse_html_page(html.encode(),url)

    def test_normal_tender_on_same_host_keeps_real_document_links(self):
        html=b'<html><p>Maintenance equipment procurement</p><a href="specification.pdf">Technical specification</a></html>'
        text,links=_parse_html_page(html,'https://cloud.3p.eu/Downloads/1/2/BE/2026')
        self.assertIn('procurement',text);self.assertEqual(len(links),1)

    def test_unrelated_or_long_documents_are_not_classified_from_one_word(self):
        self.assertIsNone(html_access_barrier(b'<html>maintenance terms country</html>','https://ekr.gov.hu/notice'))
        self.assertIsNone(html_access_barrier('Sajnáljuk, karbantartást végzünk'.encode(),'https://other.example/notice'))


if __name__=='__main__':unittest.main()
