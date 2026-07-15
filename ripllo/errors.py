"""Typed error class for the Ripllo SDK."""

from __future__ import annotations

from typing import Optional


class RiplloError(Exception):
    """Raised on any Ripllo API failure — non-2xx HTTP, enveloped error
    bodies (``data=null``, ``error.code/message``), transport failures,
    timeouts, and malformed responses.

    Attributes
    ----------
    status:
        HTTP status code. ``0`` for transport-level errors (network,
        timeout, non-JSON response received before the request reached
        the API).
    code:
        Machine-readable error code. For server-side errors this is the
        ``error.code`` field of the response envelope. For client-side
        failures one of ``timeout`` / ``network_error`` /
        ``invalid_response`` / ``unknown``.
    message:
        Human-readable error message.
    request_id:
        The ``meta.requestId`` field of the response envelope, when
        present — useful for support tickets.
    """

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.request_id = request_id

    def __repr__(self) -> str:
        return (
            f"RiplloError(status={self.status}, code={self.code!r}, "
            f"message={self.message!r})"
        )
