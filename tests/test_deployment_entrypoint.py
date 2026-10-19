"""Exercise the production entrypoint across public and protected boundaries."""
import importlib
import json
import threading
import tomllib
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]

class DeploymentEntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config=tomllib.loads((ROOT/'pyproject.toml').read_text())
        module,name=config['tool']['vercel']['entrypoint'].split(':')
        handler=getattr(importlib.import_module(module),name)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_public_pages_and_handoff_assets_are_reachable(self):
        for route,marker in [('/',b'GLOBAL'),('/web/ecosystem.html',b'businessTransfer'),
                             ('/web/ecosystem.js',b'transferFields'),('/customer',b'iframe'),
                             ('/account',b'Global Broker')]:
            with self.subTest(route=route),urlopen(self.base+route) as response:
                self.assertEqual(response.status,200)
                self.assertIn(marker,response.read())

    def test_private_data_still_requires_authentication(self):
        for route in ['/api/private_room','/api/admin_opportunities']:
            with self.subTest(route=route),self.assertRaises(HTTPError) as error:
                urlopen(self.base+route)
            self.assertEqual(error.exception.code,401)

    def test_static_path_cannot_read_repository_files(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base+'/web/../pyproject.toml')
        self.assertEqual(error.exception.code,403)
