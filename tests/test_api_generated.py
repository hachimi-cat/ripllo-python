"""client.api: every feature route, one method each, generated from the API spec
(scripts/apigen.sh). Calls are signed like every other request."""

from __future__ import annotations

import json
from typing import Any, List
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from ripllo import RiplloClient


def _client(seen: List[httpx.Request]) -> RiplloClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = {"data": {"ok": True}, "error": None, "meta": {"requestId": "r"}}
        return httpx.Response(200, content=json.dumps(body).encode())

    http = httpx.Client(transport=httpx.MockTransport(handler))
    return RiplloClient(key_id="AKIARPLOTEST", secret="sk", base_url="https://ripllo.test", http=http)


def test_create_sends_the_fields_ripllo_validates_signed() -> None:
    seen: List[httpx.Request] = []
    client = _client(seen)
    client.api.discount_codes_create(code="SPRING10", type_="percent", value=10, currency="IDR", public=False)
    request = seen[0]
    assert (request.method, request.url.path) == ("POST", "/api/v1/discount-codes")
    assert json.loads(request.content) == {"code": "SPRING10", "type": "percent", "value": 10, "currency": "IDR", "public": False}
    assert request.headers["authorization"].startswith("Ripllo-HMAC-SHA256 keyId=AKIARPLOTEST")
    assert request.headers.get("idempotency-key")


def test_path_and_query() -> None:
    seen: List[httpx.Request] = []
    client = _client(seen)
    client.api.discount_codes_get("dc 1")
    client.api.discount_codes_list(limit=5, active="true")
    assert seen[0].url.raw_path.decode() == "/api/v1/discount-codes/dc%201"
    assert seen[1].url.path == "/api/v1/discount-codes"
    assert parse_qs(urlsplit(str(seen[1].url)).query) == {"limit": ["5"], "active": ["true"]}


def test_a_required_field_is_asked_for() -> None:
    client = _client([])
    with pytest.raises(ValueError, match="needs code"):
        client.api.discount_codes_create(type_="percent", value=10, currency="IDR")


def test_every_feature_route_has_a_method() -> None:
    methods = [n for n in dir(_client([]).api) if not n.startswith("_")]
    assert len(methods) > 200


def test_a_boolean_query_is_sent_as_the_server_reads_it() -> None:
    """A Catent proof found ?active=True ignored by Ripllo (it reads 'true')."""
    seen: List[httpx.Request] = []
    client = _client(seen)
    client.discount_codes.list(active=True)
    client.api.discount_codes_list(active=False)
    assert parse_qs(urlsplit(str(seen[0].url)).query)["active"] == ["true"]
    assert parse_qs(urlsplit(str(seen[1].url)).query)["active"] == ["false"]
