import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MembershipContractTests(unittest.TestCase):
    def test_catalog_matches_published_monthly_prices(self):
        policy = (ROOT/'web/pricing-policy.js').read_text()
        schema = (ROOT/'sql/membership_requests.sql').read_text()
        for plan in ['sector','multi','global']:
            price = int(re.search(plan+r':\{[^\n]*?monthlyUsd:(\d+)', policy).group(1))*100
            self.assertIn("when '"+plan+"' then "+str(price), schema)
            self.assertRegex(schema, "'id','"+plan+"'.*?'amount_minor',"+str(price))

    def test_route_and_account_entry_are_packaged_for_both_hosts(self):
        routes = json.loads((ROOT/'vercel.json').read_text())['rewrites']
        self.assertIn({'source':'/membership','destination':'/web/membership.html'}, routes)
        self.assertIn('"/membership": "membership.html"', (ROOT/'render_server.py').read_text())
        self.assertIn('href="/membership"', (ROOT/'web/account.html').read_text())

    def test_membership_never_issues_entitlement_or_invoice_updates(self):
        schema = (ROOT/'sql/membership_requests.sql').read_text()
        self.assertNotRegex(schema.lower(), r'(update|insert into)\s+public\.customer_entitlements')
        self.assertIn("check(invoice_status='not_issued')", schema)
        self.assertIn("check(status='awaiting_provider')", schema)
