"""High-level Ripllo client wrapping every developer-facing endpoint.

Mirrors ``sdk/node/src/client.ts`` (0.2.2) at the API-surface level:
HMAC-SHA256 partner-billing auth (Pattern 2), resource namespaces for
every route group, and a generic ``passthrough`` for partners that
need to relay arbitrary merchant-portal requests.

Auth scheme
-----------

Every request is signed with::

    Authorization: Ripllo-HMAC-SHA256 keyId=<keyId>, scope=*, signature=<hex>
    X-Ripllo-Timestamp: <unix_seconds>

where::

    signature = HMAC-SHA256(secret, f"{METHOD}\\n{PATH}\\n{TIMESTAMP}\\n{BODY_SHA256}")

with an optional trailing ``"\\n<idempotencyKey>"`` segment when the
request carries an ``Idempotency-Key`` header. The path is signed
*without* the query string — the backend verifier strips the query
before reconstructing the string-to-sign.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import quote, urlencode

import httpx

from .errors import RiplloError
from .resources import build_resources


_HttpMethod = str  # one of GET / POST / PATCH / PUT / DELETE


def _qs(params: Mapping[str, Any]) -> str:
    """Render a querystring, skipping ``None`` values (Node SDK parity)."""
    filtered = {k: v for k, v in params.items() if v is not None}
    if not filtered:
        return ""
    return "?" + urlencode({k: str(v) for k, v in filtered.items()})


class RiplloClient:
    """Sign + dispatch requests to Ripllo's HMAC API.

    Parameters
    ----------
    key_id:
        HMAC access key id, e.g. ``"AKIARPLO<random>"``.
    secret:
        HMAC secret.
    base_url:
        Base URL. Default ``https://ripllo.com``.
    on_behalf_of:
        Optional merchant accountId — forwarded as
        ``X-Ripllo-On-Behalf-Of``. Only allowed when ``key_id`` holds
        the ``ripllo:platform:admin`` scope.
    timeout_ms:
        Per-request fetch timeout in milliseconds. Default 30s.
    http:
        Optional pre-built ``httpx.Client`` — pass one in to share a
        connection pool or inject a ``MockTransport`` in tests.
    """

    def __init__(
        self,
        *,
        key_id: str,
        secret: str,
        base_url: str = "https://ripllo.com",
        on_behalf_of: Optional[str] = None,
        timeout_ms: int = 30_000,
        http: Optional[httpx.Client] = None,
    ) -> None:
        if not key_id or not secret:
            raise ValueError("RiplloClient: key_id and secret are required")
        self.key_id = key_id
        self.secret = secret
        self.base_url = base_url.rstrip("/")
        self.default_on_behalf_of = on_behalf_of
        self.timeout_ms = timeout_ms
        self._http = http or httpx.Client(timeout=timeout_ms / 1000.0)
        self._owns_http = http is None

        # Resource namespaces (lazy-mounted to keep client.py readable)
        resources = build_resources(self)
        # Every feature route, one method each (generated from the API spec).
        from .api_generated import GeneratedApi

        self.api = GeneratedApi(self)
        self.discount_codes = resources["discount_codes"]
        self.pixels = resources["pixels"]
        self.feeds = resources["feeds"]
        self.blog = resources["blog"]
        self.abandoned_cart = resources["abandoned_cart"]
        self.referrals = resources["referrals"]
        self.api_keys = resources["api_keys"]
        self.webhooks = resources["webhooks"]
        self.audit_log = resources["audit_log"]
        self.integrations = resources["integrations"]
        self.billing = resources["billing"]
        self.uploads = resources["uploads"]
        self.campaigns = resources["campaigns"]
        self.programs = resources["programs"]
        self.collaborations = resources["collaborations"]
        self.insights = resources["insights"]
        self.channels = resources["channels"]
        self.contacts = resources["contacts"]
        self.contact_lists = resources["contact_lists"]
        self.broadcasts = resources["broadcasts"]
        self.marketing_campaigns = resources["marketing_campaigns"]
        self.funnels = resources["funnels"]
        self.inbox = resources["inbox"]
        self.audience_segments = resources["audience_segments"]
        self.merchant_profile = resources["merchant_profile"]
        self.creator_profile = resources["creator_profile"]
        self.affiliator_profile = resources["affiliator_profile"]
        self.marketplace = resources["marketplace"]
        self.affiliates = resources["affiliates"]
        self.kyc = resources["kyc"]
        self.creator_stats = resources["creator_stats"]
        self.admin = resources["admin"]

    # ─── Lifecycle ───────────────────────────────────────────────

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "RiplloClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def for_merchant(self, account_id: str) -> "RiplloClient":
        """Clone scoped to a specific merchant. Use with platform-admin keys."""
        return RiplloClient(
            key_id=self.key_id,
            secret=self.secret,
            base_url=self.base_url,
            on_behalf_of=account_id,
            timeout_ms=self.timeout_ms,
            # Share the underlying http client so callers can still mock it.
            http=self._http,
        )

    # ─── HMAC signing ────────────────────────────────────────────

    def _sign(
        self,
        method: _HttpMethod,
        path: str,
        body: Optional[str],
        idempotency_key: Optional[str],
    ) -> tuple[str, str]:
        ts = str(int(time.time()))
        body_hash = hashlib.sha256((body or "").encode("utf-8")).hexdigest()
        idem = f"\n{idempotency_key}" if idempotency_key else ""
        # Sign the path WITHOUT query string. The backend verifier strips
        # the query before reconstructing the string-to-sign — this is the
        # same fix as the Node SDK 0.2.x.
        path_to_sign = path.split("?", 1)[0]
        string_to_sign = (
            f"{method.upper()}\n{path_to_sign}\n{ts}\n{body_hash}{idem}"
        )
        signature = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature, ts

    @staticmethod
    def _gen_idem() -> str:
        return f"idem_{uuid.uuid4()}"

    # ─── Low-level request ───────────────────────────────────────

    def request(
        self,
        *,
        method: _HttpMethod,
        path: str,
        body: Any = None,
        idempotency_key: Optional[str] = None,
        on_behalf_of: Optional[str] = None,
    ) -> Any:
        body_json: Optional[str]
        if body is not None:
            body_json = json.dumps(body, separators=(",", ":"))
        else:
            body_json = None

        signature, timestamp = self._sign(method, path, body_json, idempotency_key)

        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Authorization": (
                f"Ripllo-HMAC-SHA256 keyId={self.key_id}, scope=*, "
                f"signature={signature}"
            ),
            "X-Ripllo-Timestamp": timestamp,
        }
        if body_json is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        effective_obo = on_behalf_of or self.default_on_behalf_of
        if effective_obo:
            headers["X-Ripllo-On-Behalf-Of"] = effective_obo

        url = f"{self.base_url}{path}"
        try:
            res = self._http.request(
                method.upper(),
                url,
                headers=headers,
                content=body_json,
                timeout=self.timeout_ms / 1000.0,
            )
        except httpx.TimeoutException as e:
            raise RiplloError(
                0, "timeout", f"Ripllo request timed out after {self.timeout_ms}ms"
            ) from e
        except httpx.HTTPError as e:
            raise RiplloError(0, "network_error", str(e)) from e

        text = res.text
        try:
            envelope = json.loads(text) if text else {}
        except ValueError:
            raise RiplloError(
                res.status_code,
                "invalid_response",
                f"Non-JSON response: {text[:200]}",
            ) from None

        err = envelope.get("error") if isinstance(envelope, dict) else None
        meta = envelope.get("meta") if isinstance(envelope, dict) else None
        request_id = meta.get("requestId") if isinstance(meta, dict) else None

        if res.status_code >= 400 or err:
            code = (err or {}).get("code", "unknown")
            message = (err or {}).get("message", f"HTTP {res.status_code}")
            raise RiplloError(res.status_code, code, message, request_id)

        return envelope.get("data") if isinstance(envelope, dict) else envelope

    # ─── Generic passthrough ─────────────────────────────────────

    def _apigen_request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        body: Any = None,
    ) -> Any:
        """The call behind ``client.api.*`` (api_generated.py): signed like every other
        request, with an idempotency key on writes."""
        return self.request(
            method=method,
            path=path + _qs(query or {}),
            body=body,
            idempotency_key=None if method.upper() == "GET" else self._gen_idem(),
        )

    def passthrough(
        self,
        method: _HttpMethod,
        path: str,
        body: Any = None,
    ) -> Any:
        """Forward an arbitrary merchant-portal request through to Ripllo.

        For partners (storlaunch / fulkruma) that need to relay
        requests without hand-writing a typed method per resource.
        Returns the parsed ``data`` field of Ripllo's envelope. Errors
        surface as :class:`RiplloError`.
        """
        return self.request(method=method, path=path, body=body)


__all__ = ["RiplloClient", "_qs", "quote"]
