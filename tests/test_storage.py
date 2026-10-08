import unittest
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


if __name__ == "__main__":
    unittest.main()
