"""Official Python SDK for Ripllo.

Mirrors the surface of ``@forjio/ripllo-node`` 0.2.2: discounts,
referrals, abandoned cart, pixels, feeds, blog + creator marketplace
(campaigns, programs, collaborations), marketing (channels, contacts,
contact-lists, marketing campaigns, funnels, inbox, audience segments),
insights, API keys, audit log, billing, integrations, uploads,
profiles (merchant/creator/affiliator), KYC, disputes.

Auth is Pattern 2 HMAC partner-billing — same scheme storlaunch +
fulkruma use against ripllo's backend.

Quickstart
----------

::

    from ripllo import RiplloClient

    rip = RiplloClient(
        key_id="AKIARPLO...",
        secret="...",
        on_behalf_of="acc_storlaunch_merchant_123",   # optional
    )

    # Typed methods
    rip.discount_codes.list(limit=20)
    rip.referrals.get_program()

    # Webhook verification
    from ripllo import verify_webhook
    event = verify_webhook(
        raw_body=request.body,
        signature=request.headers["Ripllo-Signature"],
        secret=os.environ["RIPLLO_WEBHOOK_SECRET"],
    )
"""

from .client import RiplloClient
from .errors import RiplloError
from .webhooks import verify_webhook

__all__ = [
    "RiplloClient",
    "RiplloError",
    "verify_webhook",
]

__version__ = "0.1.3"
