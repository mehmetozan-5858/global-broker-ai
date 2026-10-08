import os
import unittest

from api.private_room import _build_access, _session_from_headers
from src.session_security import SessionError, issue_session


SECRET = "s" * 32


class Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class TestPrivateRoomAuth(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("PRIVATE_ROOM_SESSION_SECRET")
        os.environ["PRIVATE_ROOM_SESSION_SECRET"] = SECRET

    def tearDown(self):
        if self.old is None:
            os.environ.pop("PRIVATE_ROOM_SESSION_SECRET", None)
        else:
            os.environ["PRIVATE_ROOM_SESSION_SECRET"] = self.old

    def test_signed_session_is_accepted(self):
        token = issue_session("buyer-user", SECRET)
        session = _session_from_headers(Headers(Authorization="Bearer " + token))
        self.assertEqual(session["sub"], "buyer-user")

    def test_missing_token_is_rejected(self):
        with self.assertRaises(SessionError):
            _session_from_headers(Headers())

    def test_tampered_token_is_rejected(self):
        token = issue_session("buyer-user", SECRET)
        token = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(SessionError):
            _session_from_headers(Headers(Authorization="Bearer " + token))

    def test_consent_events_control_access(self):
        record = {
            "access": {
                "party_verified": True,
                "terms_signed": True,
                "access_fee_required": False,
                "access_paid": False,
            },
            "consent_events": [
                {"opportunity_id": "opp-1", "party": "buyer", "actor_id": "b", "action": "grant", "timestamp": "2026-10-08T18:00:00Z"},
                {"opportunity_id": "opp-1", "party": "seller", "actor_id": "s", "action": "grant", "timestamp": "2026-10-08T18:01:00Z"},
            ],
        }
        access = _build_access(record, "opp-1")
        self.assertTrue(access.buyer_consent)
        self.assertTrue(access.seller_consent)

    def test_revoked_consent_closes_gate(self):
        record = {
            "access": {"party_verified": True, "terms_signed": True},
            "consent_events": [
                {"opportunity_id": "opp-1", "party": "buyer", "actor_id": "b", "action": "grant", "timestamp": "2026-10-08T18:00:00Z"},
                {"opportunity_id": "opp-1", "party": "seller", "actor_id": "s", "action": "grant", "timestamp": "2026-10-08T18:01:00Z"},
                {"opportunity_id": "opp-1", "party": "seller", "actor_id": "s", "action": "revoke", "timestamp": "2026-10-08T18:02:00Z"},
            ],
        }
        access = _build_access(record, "opp-1")
        self.assertTrue(access.buyer_consent)
        self.assertFalse(access.seller_consent)


if __name__ == "__main__":
    unittest.main()
