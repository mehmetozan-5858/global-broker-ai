import unittest
import subprocess
from pathlib import Path

HTML=(Path(__file__).resolve().parents[1]/"web"/"admin.html").read_text(encoding="utf-8")

class AdminTenderContentTests(unittest.TestCase):
    def test_direct_content_instead_of_raw_links(self):
        self.assertIn("body=adminTenderContent(o)",HTML)
        self.assertIn("Teknik şartlar",HTML)
        self.assertIn("Katılım / yeterlilik koşulları",HTML)
        self.assertIn("Başvuru belgeleri, teminat ve ödeme",HTML)
        self.assertIn("Resmî bağlantılar (isteğe bağlı)",HTML)
    def test_no_unverified_readiness_claim(self):
        self.assertNotIn("✅ Yönetici ön incelemesine hazır",HTML)
        self.assertIn("şartname teyidi gerekli",HTML)
    def test_links_are_capped(self):
        self.assertIn("}).slice(0,3)",HTML)

    def test_rendered_read_status_and_dynamic_pdf_link(self):
        script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('web/admin.html','utf8');
const fn=html.slice(html.indexOf('function adminTenderContent('),html.indexOf("var activeTab='overview'"));
const context={urls:()=>[{v:'https://ted.europa.eu/en/notice/123',k:'source'}],
  uniqueText:v=>v||'',pick:()=>'',txt:v=>String(v||''),kv:()=>'',
  productText:()=>'',title:()=>'',buyer:()=>'',summary:()=>'',quantity:()=>'',budget:()=>'',locationText:()=>'',
  evidenceBlock:()=>'',esc:v=>String(v)};
vm.createContext(context);vm.runInContext(fn,context);
const page=context.adminTenderContent({document_extraction:{parsed_count:5},specification_analysis:{source_page_parsed:true,parsed_document_count:0}});
assert(page.includes('Kaynak sayfası okundu.'));
assert(page.includes('Ek belge okuması doğrulanamadı.'));
assert(!page.includes('ek belge okundu.'));
const pdf=context.adminTenderContent({specification_analysis:{parsed_document_count:1,unparsed_attachment_count:2,documents:[{url:'https://example.test/download?id=5',kind:'pdf',parse_status:'parsed'}]}});
assert(pdf.includes('1 ek belge okundu.'));
assert(pdf.includes('Okunmayı bekleyen ek: 2.'));
assert(pdf.indexOf('https://example.test/download?id=5')<pdf.indexOf('https://ted.europa.eu/en/notice/123'));
'''
        result = subprocess.run(["node", "-e", script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__=="__main__":
    unittest.main()
