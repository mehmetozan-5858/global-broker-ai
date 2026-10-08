import unittest

from src.access_control import AccessRecord, evaluate_access, private_view


class TestAccessControl(unittest.TestCase):
    def test_authentication_required(self):
        self.assertIn("authentication", evaluate_access(AccessRecord())["missing"])

    def test_payment_never_overrides_consent(self):
        r = AccessRecord(authenticated=True, party_verified=True, access_fee_required=True,
                         access_paid=True, terms_signed=True)
        d = evaluate_access(r)
        self.assertFalse(d["allowed"])
        self.assertIn("buyer_consent", d["missing"])
        self.assertIn("seller_consent", d["missing"])
        self.assertFalse(d["payment_overrides_consent"])

    def test_signed_terms_required(self):
        r = AccessRecord(authenticated=True, party_verified=True,
                         buyer_consent=True, seller_consent=True)
        self.assertIn("signed_brokerage_terms", evaluate_access(r)["missing"])

    def test_required_payment_must_be_confirmed(self):
        r = AccessRecord(authenticated=True, party_verified=True,
                         buyer_consent=True, seller_consent=True,
                         terms_signed=True, access_fee_required=True)
        self.assertIn("confirmed_access_payment", evaluate_access(r)["missing"])

    def test_all_gates_allow_introduction(self):
        r = AccessRecord(authenticated=True, party_verified=True,
                         buyer_consent=True, seller_consent=True,
                         terms_signed=True, access_fee_required=True,
                         access_paid=True)
        d = evaluate_access(r)
        self.assertTrue(d["allowed"])
        self.assertTrue(d["can_reveal_contacts"])

    def test_blocked_view_redacts_identity(self):
        opportunity = {"id": "x", "title_tr": "Test", "buyer-name": "Secret Buyer",
                       "buyer_email": "secret@example.com", "source": "TEST"}
        view = private_view(opportunity, AccessRecord(authenticated=True))
        self.assertEqual(view["opportunity"]["id"], "x")
        self.assertNotIn("buyer-name", view["opportunity"])
        self.assertNotIn("buyer_email", view["opportunity"])

    def test_allowed_view_can_include_private_fields(self):
        opportunity = {"id": "x", "buyer-name": "Buyer", "buyer_email": "b@example.com"}
        r = AccessRecord(authenticated=True, party_verified=True,
                         buyer_consent=True, seller_consent=True,
                         terms_signed=True)
        self.assertEqual(private_view(opportunity, r)["opportunity"]["buyer-name"], "Buyer")


if __name__ == "__main__":
    unittest.main()
