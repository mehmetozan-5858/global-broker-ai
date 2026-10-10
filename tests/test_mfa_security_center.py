import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MfaSecurityCenterTests(unittest.TestCase):
    def test_security_route_and_totp_flow_are_present(self):
        routes = {x["source"]: x["destination"] for x in json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["rewrites"]}
        self.assertEqual(routes["/security"], "/web/security.html")
        html = (ROOT / "web/security.html").read_text(encoding="utf-8")
        self.assertIn("auth.mfa.enroll", html)
        self.assertIn("auth.mfa.challenge", html)
        self.assertIn("auth.mfa.verify", html)
        self.assertIn("factorType:'totp'", html)
        self.assertIn("AAL2", html)
        self.assertIn("SMS sağlayıcısı", html)

    def test_admin_gate_points_to_security_center_and_requires_aal2(self):
        html = (ROOT / "web/app-shell.html").read_text(encoding="utf-8")
        self.assertIn('href="/security"', html)
        self.assertIn("claims.aal!=='aal2'", html)
        self.assertIn("x.role==='admin'", html)


if __name__ == "__main__":
    unittest.main()
