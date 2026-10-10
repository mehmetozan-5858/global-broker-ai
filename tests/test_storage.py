import json
import unittest
from urllib import error
from unittest.mock import patch

from src.storage import (
    EnvJsonRecordStore,
    HttpJsonRecordStore,
    StorageError,
    build_record_store,
)


class TestStorageAdapters(unittest.TestCase):
    def test_production_without_durable_store_fails_closed(self):
        with self.assertRaises(StorageError):
            build_record_store({})

    def test_env_fallback_requires_explicit_opt_in(self):
        env = {
            "PRIVATE_ROOM_ALLOW_ENV_FALLBACK": "true",
            "PRIVATE_ROOM_RECORDS_JSON": '{"opp-1":{"opportunity":{"id":"opp-1"}}}',
        }
        store = build_record_store(env)
        self.assertIsInstance(store, EnvJsonRecordStore)
        self.assertEqual(store.get_opportunity_record("opp-1")["opportunity"]["id"], "opp-1")

    def test_env_fallback_is_forbidden_on_vercel_production(self):
        env = {
            "VERCEL_ENV": "production",
            "PRIVATE_ROOM_ALLOW_ENV_FALLBACK": "true",
            "PRIVATE_ROOM_RECORDS_JSON": '{"opp-1":{"opportunity":{"id":"opp-1"}}}',
        }
        with self.assertRaises(StorageError) as ctx:
            build_record_store(env)
        self.assertEqual(str(ctx.exception), "durable_store_not_configured")

    def test_env_fallback_is_forbidden_on_node_production(self):
        env = {
            "NODE_ENV": "production",
            "PRIVATE_ROOM_ALLOW_ENV_FALLBACK": "true",
        }
        with self.assertRaises(StorageError):
            build_record_store(env)

    def test_production_prefers_durable_store_even_with_fallback_enabled(self):
        env = {
            "VERCEL_ENV": "production",
            "PRIVATE_ROOM_STORE_URL": "https://store.example.test/opportunities",
            "PRIVATE_ROOM_ALLOW_ENV_FALLBACK": "true",
        }
        self.assertIsInstance(build_record_store(env), HttpJsonRecordStore)

    def test_env_store_cannot_write_consent(self):
        store = EnvJsonRecordStore("{}")
        with self.assertRaises(StorageError) as ctx:
            store.record_consent("opp-1", "buyer-1", "grant")
        self.assertEqual(str(ctx.exception), "env_store_is_read_only")

    def test_durable_store_has_priority_over_env_fallback(self):
        env = {
            "PRIVATE_ROOM_STORE_URL": "https://store.example.test/opportunities",
            "PRIVATE_ROOM_STORE_TOKEN": "secret",
            "PRIVATE_ROOM_ALLOW_ENV_FALLBACK": "true",
            "PRIVATE_ROOM_RECORDS_JSON": '{"opp-1":{"opportunity":{"id":"wrong"}}}',
        }
        store = build_record_store(env)
        self.assertIsInstance(store, HttpJsonRecordStore)
        self.assertEqual(store.bearer_token, "secret")

    def test_http_store_rejects_plain_http(self):
        store = HttpJsonRecordStore("http://unsafe.example.test", "")
        with self.assertRaises(StorageError):
            store.get_opportunity_record("opp-1", bearer_token="oidc")

    def test_http_store_requires_auth_before_network_call(self):
        store = HttpJsonRecordStore("https://store.example.test/opportunities", "")
        with patch("src.storage.request.urlopen") as urlopen:
            with self.assertRaises(StorageError) as ctx:
                store.get_opportunity_record("opp-1")
        self.assertEqual(str(ctx.exception), "durable_store_authentication_required")
        urlopen.assert_not_called()

    def test_env_store_invalid_json_raises(self):
        store = EnvJsonRecordStore("not-json")
        with self.assertRaises(StorageError):
            store.get_opportunity_record("opp-1")

    @patch("src.storage.request.urlopen")
    def test_http_store_uses_query_id_and_runtime_oidc(self, urlopen):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"record":{"opportunity":{"id":"opp 1"}}}'

        urlopen.return_value = Response()
        store = HttpJsonRecordStore(
            "https://store.example.test/functions/v1/private-room-store", "configured-fallback"
        )
        result = store.get_opportunity_record("opp 1", bearer_token="runtime-oidc")
        self.assertEqual(result["opportunity"]["id"], "opp 1")

        req = urlopen.call_args.args[0]
        self.assertEqual(
            req.full_url,
            "https://store.example.test/functions/v1/private-room-store?id=opp+1",
        )
        self.assertEqual(req.get_header("Authorization"), "Bearer runtime-oidc")

    @patch("src.storage.request.urlopen")
    def test_http_store_extracts_record_wrapper(self, urlopen):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"record":{"opportunity":{"id":"opp-1"}}}'

        urlopen.return_value = Response()
        store = HttpJsonRecordStore("https://store.example.test/opportunities", "secret")
        result = store.get_opportunity_record("opp-1")
        self.assertEqual(result["opportunity"]["id"], "opp-1")

    @patch("src.storage.request.urlopen")
    def test_record_consent_posts_actor_from_backend(self, urlopen):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self):
                return b'{"status":"CONSENT_RECORDED","party":"buyer","action":"grant","occurred_at":"2026-10-08T19:00:00Z"}'

        urlopen.return_value = Response()
        store = HttpJsonRecordStore("https://store.example.test/functions/v1/private-room-store", "")
        result = store.record_consent("opp-1", "buyer-user", "grant", bearer_token="runtime-oidc")
        self.assertEqual(result["party"], "buyer")

        req = urlopen.call_args.args[0]
        self.assertEqual(req.method, "POST")
        self.assertEqual(req.get_header("Authorization"), "Bearer runtime-oidc")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body, {"opportunity_id": "opp-1", "actor_id": "buyer-user", "action": "grant"})

    @patch("src.storage.request.urlopen")
    def test_record_consent_maps_403_to_authorization_error(self, urlopen):
        urlopen.side_effect = error.HTTPError(
            "https://store.example.test", 403, "Forbidden", {}, None
        )
        store = HttpJsonRecordStore("https://store.example.test/functions/v1/private-room-store", "")
        with self.assertRaises(StorageError) as ctx:
            store.record_consent("opp-1", "intruder", "grant", bearer_token="runtime-oidc")
        self.assertEqual(str(ctx.exception), "consent_subject_not_authorized")

    def test_record_consent_rejects_unknown_action_without_network(self):
        store = HttpJsonRecordStore("https://store.example.test/functions/v1/private-room-store", "")
        with patch("src.storage.request.urlopen") as urlopen:
            with self.assertRaises(StorageError) as ctx:
                store.record_consent("opp-1", "buyer-user", "approve", bearer_token="runtime-oidc")
        self.assertEqual(str(ctx.exception), "invalid_consent_action")
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
