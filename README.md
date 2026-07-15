# ripllo (Python)

Official Python SDK for [Ripllo](https://ripllo.com) — Forjio's
marketing / creator-marketplace product. Mirrors the surface of
[`@forjio/ripllo-node`](https://www.npmjs.com/package/@forjio/ripllo-node)
0.2.2 1:1.

## Install

```bash
pip install ripllo
```

## Auth

Ripllo uses **Pattern 2 HMAC partner-billing** — same scheme
Storlaunch and Fulkruma use to talk to Ripllo. Every request is signed
with HMAC-SHA256 over `METHOD\nPATH\nTIMESTAMP\nSHA256(BODY)` (plus an
optional trailing `\nIDEMPOTENCY_KEY` segment).

```python
from ripllo import RiplloClient

rip = RiplloClient(
    key_id="AKIARPLO...",
    secret="...",
    base_url="https://ripllo.com",  # default
)
```

For platform-admin keys, scope a single client to a specific merchant
by passing `on_behalf_of=...` or calling `rip.for_merchant(account_id)`.

## Resources

Every Node SDK namespace is reproduced as a snake_case attribute on
the Python client:

| Node | Python |
|---|---|
| `discountCodes` | `discount_codes` |
| `pixels` | `pixels` |
| `feeds` | `feeds` |
| `blog` | `blog` |
| `abandonedCart` | `abandoned_cart` |
| `referrals` | `referrals` |
| `apiKeys` | `api_keys` |
| `webhooks` | `webhooks` |
| `auditLog` | `audit_log` |
| `integrations` | `integrations` |
| `billing` | `billing` |
| `uploads` | `uploads` |
| `campaigns` | `campaigns` |
| `programs` | `programs` |
| `collaborations` | `collaborations` |
| `insights` | `insights` |
| `channels` | `channels` |
| `contacts` | `contacts` |
| `contactLists` | `contact_lists` |
| `broadcasts` | `broadcasts` (alias: `marketing_campaigns`) |
| `funnels` | `funnels` |
| `inbox` | `inbox` |
| `audienceSegments` | `audience_segments` |
| `merchantProfile` | `merchant_profile` |
| `creatorProfile` | `creator_profile` |
| `affiliatorProfile` | `affiliator_profile` |
| `marketplace` | `marketplace` |
| `affiliates` | `affiliates` |
| `kyc` | `kyc` |
| `creatorStats` | `creator_stats` |
| `admin` | `admin` |

Method names follow the same translation (`listEnrollments` →
`list_enrollments`, `setSteps` → `set_steps`, etc.). The short
aliases shipped in Node 0.2.1 are preserved.

A couple of method names collide with Python keywords and get a
trailing underscore:

- `contacts.import` (Node) → `contacts.import_` (Python)
- `admin.partnerUsage({ from, to })` → `admin.partner_usage(from_=..., to=...)`

## Examples

```python
# List discount codes
rip.discount_codes.list(limit=20)

# Create a referral program
rip.referrals.put_program({
    "rewardType": "percent",
    "referrerValue": 10,
    "refereeValue": 5,
    "currency": "IDR",
})

# Storefront-public read of merchant pixels
rip.pixels.public("acc_abc123")

# Generic passthrough — for partner backends relaying merchant-portal
# requests without hand-writing a typed method per resource.
rip.passthrough("GET", "/api/v1/some/route")
```

## Webhooks

```python
from flask import Flask, request, abort
from ripllo import verify_webhook, RiplloError
import os

app = Flask(__name__)
SECRET = os.environ["RIPLLO_WEBHOOK_SECRET"]

@app.post("/webhooks/ripllo")
def ripllo_webhook():
    try:
        event = verify_webhook(
            raw_body=request.get_data(),  # bytes, unparsed!
            signature=request.headers.get("Ripllo-Signature"),
            secret=SECRET,
        )
    except RiplloError:
        abort(400)
    # event = {"id": ..., "type": ..., "occurredAt": ..., "data": ..., "metadata": ...}
    return "", 204
```

## Errors

All failures raise `RiplloError(status, code, message, request_id)`.
`status=0` indicates a transport-level error (network / timeout /
non-JSON response). Higher statuses come from the API envelope.

## Versioning

This SDK targets the Ripllo API surface of `@forjio/ripllo-node`
0.2.2. Both packages are versioned independently — the
HMAC-signing wire protocol is stable across both.

## License

MIT
