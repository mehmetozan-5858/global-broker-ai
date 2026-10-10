import unittest
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]/"web"
class Tags(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.ids=set();self.headings=[];self.metas=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a":self.links.append(a.get("href",""))
        if a.get("id"):self.ids.add(a["id"])
        if tag in ("h1","h2"):self.headings.append(tag)
        if tag=="meta":self.metas.append(a)

class ProfessionalWebTests(unittest.TestCase):
    def test_public_site_sections_and_local_links(self):
        html=(ROOT/"website.html").read_text(encoding="utf-8")
        p=Tags();p.feed(html)
        for section in ("main","platform","urunler","pazarlar","surec","sss"):
            self.assertIn(section,p.ids)
        self.assertEqual(p.headings.count("h1"),1)
        for href in p.links:
            if href.startswith("#"):self.assertIn(href[1:],p.ids)
            elif not href.startswith(("https:","mailto:")):self.assertTrue((ROOT/href).exists(),href)
        self.assertIn("Geliştirme",html)
        self.assertIn("fiziksel ürün",html.lower())
        self.assertNotIn("garantili kazanç",html.lower())
    def test_public_admin_dashboard_is_not_authentication(self):
        for name in ("admin.html","app.html"):
            html=(ROOT/name).read_text(encoding="utf-8")
            self.assertIn('name="robots" content="noindex,nofollow"',html)
        self.assertNotIn('href="admin.html"',(ROOT/"website.html").read_text(encoding="utf-8"))
    def test_scheduled_broker_script_imports_without_pythonpath(self):
        root=ROOT.parent
        script="import sys,runpy;sys.path.insert(0,'src');runpy.run_path('src/broker.py', run_name='__scan_import_test__')"
        result=subprocess.run([sys.executable,"-c",script],cwd=root,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_mobile_and_accessibility(self):
        html=(ROOT/"website.html").read_text(encoding="utf-8")
        for needle in ("width=device-width","prefers-reduced-motion","focus-visible","Ana içeriğe geç","aria-label","@media"):
            self.assertIn(needle,html)

if __name__=="__main__":
    unittest.main()
