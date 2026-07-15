"""HMAC-SHA256 signature verifier for Ripllo webhooks.

Ripllo signs every webhook delivery with::

    Ripllo-Signature: t=<unix_seconds>,v1=<hex>

where ``<hex>`` is ``HMAC-SHA256(secret, f"{t}.{rawBody}")``. The raw
bytes of the request body matter — verifying the already-parsed JSON
will re-serialise with different whitespace and the signature will
never match.

Returns the parsed event envelope on success. Raises ``RiplloError``
on bad signature, replay (timestamp older than ``tolerance_seconds``,
default 5 min), or malformed body.

Flask example::

    from flask import Flask, request, abort
    from ripllo import verify_webhook, RiplloError
    import os

    app = Flask(__name__)
    SECRET = os.environ["RIPLLO_WEBHOOK_SECRET"]

    @app.post("/webhooks/ripllo")
    def ripllo_webhook():
        try:
            event = verify_webhook(
                raw_body=request.get_data(),
                signature=request.headers.get("Ripllo-Signature"),
                secret=SECRET,
            )
        except RiplloError:
            abort(400)
        # handle event...
        return "", 204
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Union

from .errors import RiplloError


def verify_webhook(
    *,
    raw_body: Union[bytes, str],
    signature: Optional[str],
    secret: str,
    tolerance_seconds: int = 300,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Verify a Ripllo webhook signature and return the parsed event.

    Parameters
    ----------
    raw_body:
        The *unparsed* request body as received over the wire. If you
        pass a ``str``, it's encoded as UTF-8 before hashing.
    signature:
        The value of the ``Ripllo-Signature`` header.
    secret:
        The endpoint's shared signing secret.
    tolerance_seconds:
        Reject signatures older than this many seconds. Default 300
        (5 minutes) — matches Stripe/GitHub conventions.
    now:
        Inject a clock for tests; seconds since epoch.

    Returns
    -------
    Dict[str, Any]
        The parsed JSON event envelope (``id``, ``type``,
        ``occurredAt``, ``accountId``, ``data``, ``metadata``).

    Raises
    ------
    RiplloError
        On any failure — missing/malformed signature header, timestamp
        outside tolerance window, bad signature, or non-JSON body.
    """
    if not signature:
        raise RiplloError(0, "missing_signature", "missing Ripllo-Signature header")

    parts: Dict[str, str] = {}
    for segment in signature.split(","):
        if "=" not in segment:
            continue
        k, _, v = segment.partition("=")
        if k and v:
            parts[k.strip()] = v.strip()

    ts = parts.get("t")
    v1 = parts.get("v1")
    if not ts or not v1:
        raise RiplloError(0, "malformed_signature", "malformed signature header")

    try:
        ts_num = int(ts)
    except ValueError:
        raise RiplloError(0, "malformed_signature", "non-numeric timestamp") from None

    current = now if now is not None else time.time()
    drift = abs(int(current) - ts_num)
    if drift > tolerance_seconds:
        raise RiplloError(
            0,
            "signature_expired",
            f"signature timestamp {drift}s out of tolerance",
        )

    body_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    payload = f"{ts_num}.".encode("utf-8") + body_bytes
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, v1):
        raise RiplloError(0, "bad_signature", "bad signature")

    try:
        return json.loads(body_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise RiplloError(
            0,
            "invalid_body",
            "webhook body is not valid JSON",
        ) from None
