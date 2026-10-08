import unittest
from datetime import datetime, timezone

from src.session_security import SessionError, issue_session, verify_session
from src.consent_records import ConsentEvent, current_consent, mutual_consent, new_event


SECRET = "x" * 32


class TestSessionSecurity(unittest.TestCase):
    def test_valid_session(self):
        token = issue_session("party-1", SECRET, ttl_seconds=1800, now=1000)
        payload = verify_session(token, SECRET, now=1200)
        self.assertEqual(payload["sub"], "party-1")
        self.assertEqual(payload["role"], "party")

    def test_expired_session_rejected(self):
        token = issue_session("party-1", SECRET, ttl_seconds=10, now=1000)
        with self.assertRaisesRegex(SessionError, "session_expired"):
            verify_session(token, SECRET, now=1010)

    def test_tampered_session_rejected(self):
        token = issue_session("party-1", SECRET, now=1000)
        body, sig = token.split(".", 1)
        tampered = ("A" if body[0] != "A" else "B") + body[1:] + "." + sig
        with self.assertRaises(SessionError):
            verify_session(tampered, SECRET, now=1100)

    def test_short_secret_rejected(self):
        with self.assertRaisesRegex(SessionError, "secret_too_short"):
            issue_session("party-1", "short", now=1000)


class TestConsentRecords(unittest.TestCase):
    def event(self, party, action, minute):
        return new_event(
            "opp-1", party, party + "-user", action,
            now=datetime(2026, 10, 8, 18, minute, tzinfo=timezone.utc),
        )

    def test_mutual_grant(self):
        events = [self.event("buyer", "grant", 0), self.event("seller", "grant", 1)]
        self.assertTrue(mutual_consent(events, "opp-1"))

    def test_revoke_closes_access(self):
        events = [
            self.event("buyer", "grant", 0),
            self.event("seller", "grant", 1),
            self.event("buyer", "revoke", 2),
        ]
        self.assertFalse(current_consent(events, "opp-1", "buyer"))
        self.assertFalse(mutual_consent(events, "opp-1"))

    def test_other_opportunity_does_not_leak_consent(self):
        event = ConsentEvent(
            opportunity_id="other", party="buyer", actor_id="u", action="grant",
            timestamp="2026-10-08T18:00:00Z",
        )
        self.assertFalse(current_consent([event], "opp-1", "buyer"))

    def test_invalid_party_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_party"):
            new_event("opp-1", "broker", "u", "grant",
                      now=datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
