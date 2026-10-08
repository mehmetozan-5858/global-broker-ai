"""Storage adapters for Global Broker private-room records.

Production must use an explicit durable backend. Environment JSON is available
only when PRIVATE_ROOM_ALLOW_ENV_FALLBACK=true, which keeps local tests simple
without silently weakening production persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
from urllib import error, parse, request


class StorageError(RuntimeError):
    pass


class RecordStore(Protocol):
    def get_opportunity_record(
        self, opportunity_id: str, *, bearer_token: str = ""
    ) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class EnvJsonRecordStore:
    raw_json: str

    def get_opportunity_record(
        self, opportunity_id: str, *, bearer_token: str = ""
    ) -> dict[str, Any] | None:
        del bearer_token
        try:
            payload = json.loads(self.raw_json or "{}")
        except json.JSONDecodeError as exc:
            raise StorageError("invalid_env_store_json") from exc
        if not isinstance(payload, dict):
            raise StorageError("invalid_env_store_shape")
        record = payload.get(opportunity_id)
        return record if isinstance(record, dict) else None


@dataclass(frozen=True)
class HttpJsonRecordStore:
    base_url: str
    bearer_token: str = ""
    timeout_seconds: float = 4.0

    def get_opportunity_record(
        self, opportunity_id: str, *, bearer_token: str = ""
    ) -> dict[str, Any] | None:
        if not self.base_url.startswith("https://"):
            raise StorageError("durable_store_requires_https")

        parsed = parse.urlsplit(self.base_url)
        query = parse.parse_qsl(parsed.query, keep_blank_values=True)
        query.append(("id", opportunity_id))
        url = parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, parse.urlencode(query), parsed.fragment)
        )

        runtime_token = bearer_token.strip()
        configured_token = self.bearer_token.strip()
        token = runtime_token or configured_token
        if not token:
            raise StorageError("durable_store_authentication_required")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        req = request.Request(url, headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                if response.status == 204:
                    return None
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise StorageError(f"durable_store_http_{exc.code}") from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise StorageError("durable_store_unavailable") from exc
        if not isinstance(payload, dict):
            raise StorageError("durable_store_invalid_payload")
        record = payload.get("record", payload)
        return record if isinstance(record, dict) else None


def build_record_store(env: dict[str, str] | None = None) -> RecordStore:
    values = os.environ if env is None else env
    durable_url = (values.get("PRIVATE_ROOM_STORE_URL") or "").strip()
    durable_token = (values.get("PRIVATE_ROOM_STORE_TOKEN") or "").strip()
    if durable_url:
        return HttpJsonRecordStore(durable_url, durable_token)

    allow_fallback = (values.get("PRIVATE_ROOM_ALLOW_ENV_FALLBACK") or "").lower() == "true"
    if allow_fallback:
        return EnvJsonRecordStore(values.get("PRIVATE_ROOM_RECORDS_JSON") or "{}")

    raise StorageError("durable_store_not_configured")
