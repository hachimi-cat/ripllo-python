"""Resource namespaces for RiplloClient — Python parity with ripllo-node 0.2.2.

Each builder takes a ``RiplloClient`` and returns a small namespace
whose methods map 1:1 to backend REST routes. Methods accept plain
``Dict[str, Any]`` bodies — the Node SDK's typed input shapes are
documented in ``sdk/node/src/client.ts`` and ``types.ts`` but kept
loose here so partner code doesn't have to track per-route shapes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import quote

if TYPE_CHECKING:
    from .client import RiplloClient


def _qs(params: Dict[str, Any]) -> str:
    """Render a querystring, skipping ``None`` values (Node SDK parity)."""
    from urllib.parse import urlencode

    filtered = {k: v for k, v in params.items() if v is not None}
    if not filtered:
        return ""
    # true/false as the server reads them (str(True) is "True": a Catent proof found
    # ?active=True ignored, so an "active only" list returned inactive codes too)
    return "?" + urlencode(
        {k: (str(v).lower() if isinstance(v, bool) else str(v)) for k, v in filtered.items()}
    )


class _Namespace:
    def __init__(self, client: "RiplloClient") -> None:
        self.client = client


# ─── Discount codes ─────────────────────────────────────────────


class DiscountCodesResource(_Namespace):
    def list(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/discount-codes{_qs({'limit': limit, 'cursor': cursor, 'active': active})}",
        )

    def get(self, code_id: str) -> Any:
        return self.client.request(method="GET", path=f"/api/v1/discount-codes/{code_id}")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/discount-codes",
            body=input,
            idempotency_key=self.client._gen_idem(),
        )

    def update(self, code_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path=f"/api/v1/discount-codes/{code_id}", body=patch
        )

    def archive(self, code_id: str) -> Any:
        return self.client.request(
            method="DELETE", path=f"/api/v1/discount-codes/{code_id}"
        )

    def validate(self, input: Dict[str, Any]) -> Any:
        """Read-only validation for cart preview."""
        return self.client.request(
            method="POST", path="/api/v1/discount-codes/validate", body=input
        )

    def redeem(self, input: Dict[str, Any]) -> Any:
        """Idempotent redemption — call from payment-success path."""
        return self.client.request(
            method="POST", path="/api/v1/discount-codes/redeem", body=input
        )

    def applicable(
        self,
        account_id: str,
        *,
        currency: Optional[str] = None,
        product_id: Optional[str] = None,
        tags: Optional[str] = None,
        subtotal: Optional[float] = None,
    ) -> Any:
        """Public applicable-codes list for storefront teaser."""
        return self.client.request(
            method="GET",
            path=(
                f"/api/v1/discount-codes/applicable/{account_id}"
                + _qs(
                    {
                        "currency": currency,
                        "productId": product_id,
                        "tags": tags,
                        "subtotal": subtotal,
                    }
                )
            ),
        )


# ─── Pixels ─────────────────────────────────────────────────────


class PixelsResource(_Namespace):
    def get(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/pixels")

    def update(self, input: Dict[str, Any]) -> Any:
        return self.client.request(method="PATCH", path="/api/v1/pixels", body=input)

    def public(self, account_id: str) -> Any:
        """Storefront-public read; never includes CAPI secret."""
        return self.client.request(
            method="GET", path=f"/api/v1/pixels/public/{account_id}"
        )


# ─── Feeds ──────────────────────────────────────────────────────


class FeedsResource(_Namespace):
    def get_config(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/feeds/config")

    def update_config(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path="/api/v1/feeds/config", body=input
        )

    def google_feed_url(self, account_id: str) -> str:
        return f"{self.client.base_url}/api/v1/feeds/google/{account_id}.xml"


# ─── Blog ───────────────────────────────────────────────────────


class BlogResource(_Namespace):
    def list(self, *, status: Optional[str] = None) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/blog{_qs({'status': status})}"
        )

    def get(self, post_id: str) -> Any:
        return self.client.request(method="GET", path=f"/api/v1/blog/{post_id}")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/blog",
            body=input,
            idempotency_key=self.client._gen_idem(),
        )

    def update(self, post_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path=f"/api/v1/blog/{post_id}", body=patch
        )

    def delete(self, post_id: str) -> Any:
        return self.client.request(method="DELETE", path=f"/api/v1/blog/{post_id}")

    def public_list(self, account_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/blog/public/{account_id}"
        )

    def public_get(self, account_id: str, slug: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/blog/public/{account_id}/{slug}"
        )


# ─── Abandoned cart ─────────────────────────────────────────────


class AbandonedCartResource(_Namespace):
    def get_config(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/abandoned-cart/config")

    def update_config(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path="/api/v1/abandoned-cart/config", body=input
        )

    def list_reminders(self, *, limit: Optional[int] = None) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/abandoned-cart/reminders{_qs({'limit': limit})}",
        )

    def stats(self, *, window_days: Optional[int] = None) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/abandoned-cart/stats{_qs({'windowDays': window_days})}",
        )

    def record_reminder(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/abandoned-cart/reminders", body=input
        )

    def mark_recovered(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/abandoned-cart/recover", body=input
        )


# ─── Referrals ──────────────────────────────────────────────────


class ReferralsResource(_Namespace):
    def get_program(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/referrals/program")

    def put_program(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PUT", path="/api/v1/referrals/program", body=input
        )

    def stats(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/referrals/stats")

    def issue_link(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/referrals/links/issue", body=input
        )

    def resolve_link(self, account_id: str, code: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/referrals/links/{account_id}/{code}"
        )

    def record_click(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/referrals/links/click", body=input
        )

    def attribute_on_signup(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/referrals/attributions/signup",
            body=input,
        )

    def attribute_checkout_start(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/referrals/attributions/checkout-start",
            body=input,
        )

    def fulfill_reward_on_payment(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/referrals/attributions/fulfill",
            body=input,
        )

    def void_attribution_on_refund(self, checkout_session_id: str) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/referrals/attributions/void",
            body={"checkoutSessionId": checkout_session_id},
        )

    def list_my_rewards(self, account_id: str, customer_id: str) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/referrals/rewards/{account_id}/{customer_id}",
        )

    def expire_pending(self) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/referrals/sweeps/expire-pending"
        )


# ─── API keys ───────────────────────────────────────────────────


class ApiKeysResource(_Namespace):
    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/api-keys")

    def create(self, input: Optional[Dict[str, Any]] = None) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/api-keys",
            body=input or {},
            idempotency_key=self.client._gen_idem(),
        )

    def revoke(self, key_id: str) -> Any:
        return self.client.request(
            method="POST", path=f"/api/v1/api-keys/{key_id}/revoke", body={}
        )


# ─── Webhook endpoints + events ────────────────────────────────


class WebhooksResource(_Namespace):
    def list_endpoints(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/webhooks/endpoints")

    def create_endpoint(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/webhooks/endpoints",
            body=input,
            idempotency_key=self.client._gen_idem(),
        )

    def update_endpoint(self, endpoint_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH",
            path=f"/api/v1/webhooks/endpoints/{endpoint_id}",
            body=patch,
        )

    def delete_endpoint(self, endpoint_id: str) -> Any:
        return self.client.request(
            method="DELETE", path=f"/api/v1/webhooks/endpoints/{endpoint_id}"
        )

    def list_events(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        type: Optional[str] = None,
        status: Optional[str] = None,
        endpoint_id: Optional[str] = None,
    ) -> Any:
        """The delivery log: one row per event per endpoint, newest first, each with
        its ``deliveryAttempts``. ``status`` is pending, sent or failed."""
        return self.client.request(
            method="GET",
            path=f"/api/v1/webhooks/events{_qs({'limit': limit, 'cursor': cursor, 'type': type, 'status': status, 'endpointId': endpoint_id})}",
        )

    def get_event(self, event_id: str) -> Any:
        """One delivery with every attempt made at it."""
        return self.client.request(method="GET", path=f"/api/v1/webhooks/events/{quote(event_id, safe='')}")

    def retry_event(self, event_id: str) -> Any:
        """One more attempt now at a delivery (202, ``pending``); raises with 409 when it
        is already queued or its endpoint is off."""
        return self.client.request(
            method="POST", path=f"/api/v1/webhooks/events/{quote(event_id, safe='')}/retry", body={}
        )

    def list_event_types(self) -> Any:
        """Every event type Ripllo emits, with what fires it."""
        return self.client.request(method="GET", path="/api/v1/webhooks/event-types")


# ─── Audit log ──────────────────────────────────────────────────


class AuditLogResource(_Namespace):
    def list(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        since: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=(
                "/api/v1/audit-log"
                + _qs(
                    {
                        "limit": limit,
                        "cursor": cursor,
                        "since": since,
                        "eventType": event_type,
                    }
                )
            ),
        )


# ─── Integrations ───────────────────────────────────────────────


class IntegrationsResource(_Namespace):
    def status(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/integrations/status")

    def get_email(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/integrations/email")

    def update_email(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PUT", path="/api/v1/integrations/email", body=input
        )


# ─── Billing (merchant subscription to Ripllo) ─────────────────


class BillingResource(_Namespace):
    def plans(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/billing/plans")

    def current_plan(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/billing/plan")

    def subscription(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/billing/subscription")

    def usage(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/billing/usage")

    def invoices(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/billing/invoices{_qs({'limit': limit, 'cursor': cursor})}",
        )

    def checkout(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/billing/checkout", body=input
        )

    def cancel(self) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/billing/cancel", body={}
        )


# ─── Uploads ────────────────────────────────────────────────────


class UploadsResource(_Namespace):
    def sign_merchant(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/uploads/sign-merchant", body=input
        )

    def get_merchant_asset(self, *, key: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/uploads/merchant-asset{_qs({'key': key})}"
        )

    def sign(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/uploads/sign", body=input
        )

    def get_avatar(self, *, key: Optional[str] = None) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/uploads/avatar{_qs({'key': key})}"
        )

    def get_deliverable(self, *, key: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/uploads/deliverable{_qs({'key': key})}"
        )


# ─── Campaigns ──────────────────────────────────────────────────


class CampaignsResource(_Namespace):
    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/campaigns")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/campaigns",
            body=input,
            idempotency_key=self.client._gen_idem(),
        )

    def get(self, campaign_id: str) -> Any:
        return self.client.request(method="GET", path=f"/api/v1/campaigns/{campaign_id}")

    def update(self, campaign_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path=f"/api/v1/campaigns/{campaign_id}", body=patch
        )

    def invite_creator(self, campaign_id: str, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/campaigns/{campaign_id}/invitations",
            body=input,
        )

    def list_applications(self, campaign_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/campaigns/{campaign_id}/applications"
        )

    def accept_application(self, campaign_id: str, application_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/campaigns/{campaign_id}/applications/{application_id}/accept",
            body={},
        )

    def reject_application(self, campaign_id: str, application_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/campaigns/{campaign_id}/applications/{application_id}/reject",
            body={},
        )

    def analytics(self, campaign_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/campaigns/{campaign_id}/analytics"
        )


# ─── Programs ───────────────────────────────────────────────────


class ProgramsResource(_Namespace):
    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/programs")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/programs",
            body=input,
            idempotency_key=self.client._gen_idem(),
        )

    def get(self, program_id: str) -> Any:
        return self.client.request(method="GET", path=f"/api/v1/programs/{program_id}")

    def update(self, program_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path=f"/api/v1/programs/{program_id}", body=patch
        )

    def delete(self, program_id: str) -> Any:
        return self.client.request(
            method="DELETE", path=f"/api/v1/programs/{program_id}"
        )

    def list_enrollments(self, program_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/programs/{program_id}/enrollments"
        )

    def approve_enrollment(self, program_id: str, enrollment_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/programs/{program_id}/enrollments/{enrollment_id}/approve",
            body={},
        )

    def reject_enrollment(self, program_id: str, enrollment_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/programs/{program_id}/enrollments/{enrollment_id}/reject",
            body={},
        )

    def revoke_enrollment(self, program_id: str, enrollment_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/programs/{program_id}/enrollments/{enrollment_id}/revoke",
            body={},
        )

    def commissions(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/programs/commissions{_qs({'limit': limit, 'cursor': cursor})}",
        )

    # Short aliases (Node v0.2.1 parity)
    def approve(self, program_id: str, enrollment_id: str) -> Any:
        return self.approve_enrollment(program_id, enrollment_id)

    def reject(self, program_id: str, enrollment_id: str) -> Any:
        return self.reject_enrollment(program_id, enrollment_id)

    def revoke(self, program_id: str, enrollment_id: str) -> Any:
        return self.revoke_enrollment(program_id, enrollment_id)

    def enrollments(self, program_id: str) -> Any:
        return self.list_enrollments(program_id)


# ─── Collaborations ─────────────────────────────────────────────


class _CollaborationDeliverables:
    def __init__(self, parent: "CollaborationsResource") -> None:
        self._p = parent

    def approve(self, collab_id: str, deliverable_id: str) -> Any:
        return self._p.approve_deliverable(collab_id, deliverable_id)

    def reject(
        self,
        collab_id: str,
        deliverable_id: str,
        input: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self._p.reject_deliverable(collab_id, deliverable_id, input or {})

    def publish(self, collab_id: str, deliverable_id: str) -> Any:
        return self._p.publish_deliverable(collab_id, deliverable_id)

    def upload_key(
        self,
        collab_id: str,
        deliverable_id: str,
        input: Dict[str, Any],
    ) -> Any:
        return self._p.upload_deliverable_key(collab_id, deliverable_id, input)


class CollaborationsResource(_Namespace):
    def __init__(self, client: "RiplloClient") -> None:
        super().__init__(client)
        self.deliverables = _CollaborationDeliverables(self)

    def from_application(
        self,
        application_id: str,
        input: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/collaborations/from-application/{application_id}",
            body=input or {},
        )

    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/collaborations")

    def get(self, collab_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/collaborations/{collab_id}"
        )

    def upload_deliverable_key(
        self,
        collab_id: str,
        deliverable_id: str,
        input: Dict[str, Any],
    ) -> Any:
        return self.client.request(
            method="POST",
            path=(
                f"/api/v1/collaborations/{collab_id}/deliverables/"
                f"{deliverable_id}/upload-key"
            ),
            body=input,
        )

    def approve_deliverable(self, collab_id: str, deliverable_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=(
                f"/api/v1/collaborations/{collab_id}/deliverables/"
                f"{deliverable_id}/approve"
            ),
            body={},
        )

    def reject_deliverable(
        self,
        collab_id: str,
        deliverable_id: str,
        input: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self.client.request(
            method="POST",
            path=(
                f"/api/v1/collaborations/{collab_id}/deliverables/"
                f"{deliverable_id}/reject"
            ),
            body=input or {},
        )

    def publish_deliverable(self, collab_id: str, deliverable_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=(
                f"/api/v1/collaborations/{collab_id}/deliverables/"
                f"{deliverable_id}/published"
            ),
            body={},
        )

    def approve_collaboration(self, collab_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/collaborations/{collab_id}/approve",
            body={},
        )

    def cancel_collaboration(self, collab_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/collaborations/{collab_id}/cancel",
            body={},
        )

    # Short aliases (Node v0.2.1 parity)
    def approve(self, collab_id: str) -> Any:
        return self.approve_collaboration(collab_id)

    def cancel(self, collab_id: str) -> Any:
        return self.cancel_collaboration(collab_id)


# ─── Insights ───────────────────────────────────────────────────


class InsightsResource(_Namespace):
    def overview(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/insights/overview")

    def program_detail(self, program_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/insights/programs/{program_id}"
        )

    def campaign_detail(self, campaign_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/insights/campaigns/{campaign_id}"
        )

    def commissions_trend(self, *, days: Optional[int] = None) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/insights/commissions-trend{_qs({'days': days})}",
        )


# ─── Channels ───────────────────────────────────────────────────


class ChannelsResource(_Namespace):
    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/channels")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/channels", body=input
        )

    def get(self, channel_id: str) -> Any:
        return self.client.request(method="GET", path=f"/api/v1/channels/{channel_id}")

    def update(self, channel_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path=f"/api/v1/channels/{channel_id}", body=patch
        )

    def delete(self, channel_id: str) -> Any:
        return self.client.request(
            method="DELETE", path=f"/api/v1/channels/{channel_id}"
        )

    def test(self, channel_id: str) -> Any:
        return self.client.request(
            method="POST", path=f"/api/v1/channels/{channel_id}/test", body={}
        )

    def dns_records(self, channel_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/channels/{channel_id}/dns-records"
        )

    def oauth_start(self, provider: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/channels/oauth/{provider}/start"
        )

    # Short alias (Node v0.2.1 parity)
    def dns(self, channel_id: str) -> Any:
        return self.dns_records(channel_id)


# ─── Contacts ───────────────────────────────────────────────────


class ContactsResource(_Namespace):
    def list(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/contacts{_qs({'limit': limit, 'cursor': cursor, 'search': search})}",
        )

    def import_(self, input: Dict[str, Any]) -> Any:
        """``import`` is a Python keyword — use ``import_`` here."""
        return self.client.request(
            method="POST", path="/api/v1/contacts/import", body=input
        )

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/contacts", body=input
        )

    def get(self, contact_id: str) -> Any:
        return self.client.request(method="GET", path=f"/api/v1/contacts/{contact_id}")

    def update(self, contact_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path=f"/api/v1/contacts/{contact_id}", body=patch
        )

    def delete(self, contact_id: str) -> Any:
        return self.client.request(
            method="DELETE", path=f"/api/v1/contacts/{contact_id}"
        )


# ─── Contact lists ──────────────────────────────────────────────


class ContactListsResource(_Namespace):
    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/contact-lists")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/contact-lists", body=input
        )

    def get(self, list_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/contact-lists/{list_id}"
        )

    def add_member(self, list_id: str, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/contact-lists/{list_id}/members",
            body=input,
        )

    def remove_member(self, list_id: str, contact_id: str) -> Any:
        return self.client.request(
            method="DELETE",
            path=f"/api/v1/contact-lists/{list_id}/members/{contact_id}",
        )

    def delete(self, list_id: str) -> Any:
        return self.client.request(
            method="DELETE", path=f"/api/v1/contact-lists/{list_id}"
        )


# ─── Broadcasts (email/SMS blasts) ──────────────────────────────
#
# Backed by /api/v1/broadcasts. Prisma model = ``Broadcast``; DB table
# = ``MarketingCampaign`` (via @@map — kept for history).
#
# Distinct from ``MarketingCampaignsResource`` (the campaign hub) which
# lives at /api/v1/marketing-campaigns.


class _BroadcastTemplates:
    def __init__(self, parent: "BroadcastsResource") -> None:
        self._p = parent

    def list(self) -> Any:
        return self._p.list_templates()

    def create(self, input: Dict[str, Any]) -> Any:
        return self._p.create_template(input)

    def update(self, template_id: str, patch: Dict[str, Any]) -> Any:
        return self._p.update_template(template_id, patch)

    def compile(self, input: Dict[str, Any]) -> Any:
        return self._p.compile_template(input)


class BroadcastsResource(_Namespace):
    def __init__(self, client: "RiplloClient") -> None:
        super().__init__(client)
        self.templates = _BroadcastTemplates(self)

    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/broadcasts")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/broadcasts", body=input
        )

    def get(self, broadcast_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/broadcasts/{broadcast_id}"
        )

    def update(self, broadcast_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH",
            path=f"/api/v1/broadcasts/{broadcast_id}",
            body=patch,
        )

    def send(
        self,
        broadcast_id: str,
        input: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/broadcasts/{broadcast_id}/send",
            body=input or {},
            idempotency_key=self.client._gen_idem(),
        )

    def send_test(self, broadcast_id: str, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/broadcasts/{broadcast_id}/send-test",
            body=input,
        )

    def list_templates(self) -> Any:
        return self.client.request(
            method="GET", path="/api/v1/broadcasts/templates"
        )

    def create_template(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/broadcasts/templates",
            body=input,
        )

    def update_template(self, template_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH",
            path=f"/api/v1/broadcasts/templates/{template_id}",
            body=patch,
        )

    def compile_template(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/broadcasts/templates/compile",
            body=input,
        )


# ─── Marketing campaigns (hub) ──────────────────────────────────
#
# Top-level marketing-campaign hub. Groups creator briefs, affiliate
# programs, discount codes, abandoned-cart reminders, referral programs,
# blog posts, and feeds under one merchant-defined campaign. Every
# child link is optional.
#
# Backed by /api/v1/marketing-campaigns (Prisma model
# ``MarketingCampaign`` -> DB table ``MarketingProgram`` via @@map).
#
# Distinct from ``BroadcastsResource`` (email/SMS blasts), which lives
# at /api/v1/broadcasts.


class MarketingCampaignsResource(_Namespace):
    def list(
        self,
        *,
        status: Optional[Union[str, List[str]]] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Any:
        status_q: Optional[str]
        if isinstance(status, list):
            status_q = ",".join(status)
        else:
            status_q = status
        return self.client.request(
            method="GET",
            path=f"/api/v1/marketing-campaigns{_qs({'status': status_q, 'limit': limit, 'cursor': cursor})}",
        )

    def get(self, campaign_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/marketing-campaigns/{campaign_id}"
        )

    def get_full(self, campaign_id: str) -> Any:
        """GET /:id/full — hub + all linked children + perf roll-up."""
        return self.client.request(
            method="GET",
            path=f"/api/v1/marketing-campaigns/{campaign_id}/full",
        )

    def selector(self) -> Any:
        """GET /_/selector — lightweight dropdown payload (non-archived)."""
        return self.client.request(
            method="GET", path="/api/v1/marketing-campaigns/_/selector"
        )

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/marketing-campaigns",
            body=input,
            idempotency_key=self.client._gen_idem(),
        )

    def update(self, campaign_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH",
            path=f"/api/v1/marketing-campaigns/{campaign_id}",
            body=patch,
        )

    def delete(self, campaign_id: str) -> Any:
        """Soft-delete via status='archived' on the server."""
        return self.client.request(
            method="DELETE",
            path=f"/api/v1/marketing-campaigns/{campaign_id}",
        )


# ─── Funnels ────────────────────────────────────────────────────


class FunnelsResource(_Namespace):
    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/funnels")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/funnels", body=input
        )

    def get(self, funnel_id: str) -> Any:
        return self.client.request(method="GET", path=f"/api/v1/funnels/{funnel_id}")

    def update(self, funnel_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path=f"/api/v1/funnels/{funnel_id}", body=patch
        )

    def delete(self, funnel_id: str) -> Any:
        return self.client.request(
            method="DELETE", path=f"/api/v1/funnels/{funnel_id}"
        )

    def set_steps(
        self,
        funnel_id: str,
        input: Union[Dict[str, Any], List[Any]],
    ) -> Any:
        body = {"steps": input} if isinstance(input, list) else input
        return self.client.request(
            method="PUT",
            path=f"/api/v1/funnels/{funnel_id}/steps",
            body=body,
        )

    def enroll(self, funnel_id: str, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/funnels/{funnel_id}/enroll",
            body=input,
        )

    def analytics(self, funnel_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/funnels/{funnel_id}/analytics"
        )

    def list_enrollments(self, funnel_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/funnels/{funnel_id}/enrollments"
        )


# ─── Inbox ──────────────────────────────────────────────────────


class InboxResource(_Namespace):
    def list_threads(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/inbox/threads{_qs({'limit': limit, 'cursor': cursor})}",
        )

    def get_thread(self, provider: str, handle: str) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/inbox/threads/{provider}/{quote(handle, safe='')}",
        )

    def mark_read(self, thread_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/inbox/{thread_id}/read",
            body={},
        )

    def archive(self, thread_id: str) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/inbox/{thread_id}/archive",
            body={},
        )


# ─── Audience segments ──────────────────────────────────────────


class AudienceSegmentsResource(_Namespace):
    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/audience-segments")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/audience-segments", body=input
        )

    def get(self, segment_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/audience-segments/{segment_id}"
        )

    def update(self, segment_id: str, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH",
            path=f"/api/v1/audience-segments/{segment_id}",
            body=patch,
        )

    def delete(self, segment_id: str) -> Any:
        return self.client.request(
            method="DELETE", path=f"/api/v1/audience-segments/{segment_id}"
        )

    def preview(
        self,
        segment_id: str,
        input: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/audience-segments/{segment_id}/preview",
            body=input or {},
        )

    def preview_adhoc(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path="/api/v1/audience-segments/preview",
            body=input,
        )


# ─── Profiles ───────────────────────────────────────────────────


class MerchantProfileResource(_Namespace):
    def me(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/merchants/me")

    def update_me(self, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PUT", path="/api/v1/merchants/me", body=patch
        )

    def publish(self) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/merchants/me/publish", body={}
        )

    def unpublish(self) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/merchants/me/unpublish", body={}
        )

    def list(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/merchants")

    def get_by_slug(self, slug: str) -> Any:
        return self.client.request(method="GET", path=f"/api/v1/merchants/{slug}")


class CreatorProfileResource(_Namespace):
    def me(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/creator-profile/me")

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/creator-profile", body=input
        )

    def update_me(self, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path="/api/v1/creator-profile/me", body=patch
        )


class AffiliatorProfileResource(_Namespace):
    def me(self) -> Any:
        return self.client.request(
            method="GET", path="/api/v1/affiliator-profile/me"
        )

    def create(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/affiliator-profile", body=input
        )

    def update_me(self, patch: Dict[str, Any]) -> Any:
        return self.client.request(
            method="PATCH", path="/api/v1/affiliator-profile/me", body=patch
        )


# ─── Marketplace ────────────────────────────────────────────────


class MarketplaceResource(_Namespace):
    def list_creators(self, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/marketplace/creators{_qs(params or {})}",
        )

    def get_creator(self, handle: str) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/marketplace/creators/{quote(handle, safe='')}",
        )

    def list_campaigns(self, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/marketplace/campaigns{_qs(params or {})}",
        )

    def get_campaign(self, campaign_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/marketplace/campaigns/{campaign_id}"
        )

    def apply_to_campaign(self, campaign_id: str, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/marketplace/campaigns/{campaign_id}/apply",
            body=input,
        )

    def my_invitations(self) -> Any:
        return self.client.request(
            method="GET", path="/api/v1/marketplace/me/invitations"
        )

    def respond_to_invitation(
        self,
        invitation_id: str,
        input: Dict[str, Any],
    ) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/marketplace/me/invitations/{invitation_id}/respond",
            body=input,
        )

    def my_applications(self) -> Any:
        return self.client.request(
            method="GET", path="/api/v1/marketplace/me/applications"
        )

    # Short aliases (Node v0.2.1 parity)
    def apply(self, campaign_id: str, input: Dict[str, Any]) -> Any:
        return self.apply_to_campaign(campaign_id, input)

    def creators(self, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.list_creators(params)

    def creator(self, handle: str) -> Any:
        return self.get_creator(handle)

    def campaigns(self, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.list_campaigns(params)

    def campaign(self, campaign_id: str) -> Any:
        return self.get_campaign(campaign_id)

    def invitations(self) -> Any:
        return self.my_invitations()

    def respond_invitation(self, invitation_id: str, input: Dict[str, Any]) -> Any:
        return self.respond_to_invitation(invitation_id, input)


# ─── Affiliates ─────────────────────────────────────────────────


class AffiliatesResource(_Namespace):
    def list(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/affiliates{_qs({'limit': limit, 'cursor': cursor})}",
        )


# ─── KYC ────────────────────────────────────────────────────────


class KycResource(_Namespace):
    def get_status(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/kyc")

    def submit(self, input: Dict[str, Any]) -> Any:
        return self.client.request(method="POST", path="/api/v1/kyc", body=input)


# ─── Creator stats ──────────────────────────────────────────────


class CreatorStatsResource(_Namespace):
    def overview(self) -> Any:
        return self.client.request(method="GET", path="/api/v1/creator-stats")

    def connect(self, provider: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/creator-stats/connect/{provider}"
        )


# ─── Admin (Pattern 2 partner billing + KYC + disputes) ────────


class AdminResource(_Namespace):
    def provision_workspace(self, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST", path="/api/v1/admin/workspaces", body=input
        )

    def get_workspace(self, account_id: str) -> Any:
        return self.client.request(
            method="GET", path=f"/api/v1/admin/workspaces/{account_id}"
        )

    def partner_usage(
        self,
        *,
        from_: str,
        to: str,
        partner: Optional[str] = None,
    ) -> Any:
        # `from` is a Python keyword — accept `from_` and translate on send.
        return self.client.request(
            method="GET",
            path=(
                "/api/v1/admin/partner/usage"
                + _qs({"partner": partner, "from": from_, "to": to})
            ),
        )

    # KYC moderation
    def list_kyc(
        self,
        *,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/admin/kyc{_qs({'status': status, 'limit': limit})}",
        )

    def approve_kyc(self, kyc_id: str) -> Any:
        return self.client.request(
            method="POST", path=f"/api/v1/admin/kyc/{kyc_id}/approve", body={}
        )

    def reject_kyc(self, kyc_id: str, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/admin/kyc/{kyc_id}/reject",
            body=input,
        )

    # Disputes
    def list_disputes(
        self,
        *,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        return self.client.request(
            method="GET",
            path=f"/api/v1/admin/disputes{_qs({'status': status, 'limit': limit})}",
        )

    def resolve_dispute(self, dispute_id: str, input: Dict[str, Any]) -> Any:
        return self.client.request(
            method="POST",
            path=f"/api/v1/admin/disputes/{dispute_id}/resolve",
            body=input,
        )


# ─── Builder ────────────────────────────────────────────────────


def build_resources(client: "RiplloClient") -> Dict[str, Any]:
    # `broadcasts` (email/SMS blasts, /api/v1/broadcasts) and
    # `marketing_campaigns` (the campaign hub,
    # /api/v1/marketing-campaigns) are NOW two separate resources.
    # Pre-v0.5 the latter was a deprecated alias of the former; that
    # alias was removed when the central marketing-campaign hub took
    # over /api/v1/marketing-campaigns.
    return {
        "discount_codes": DiscountCodesResource(client),
        "pixels": PixelsResource(client),
        "feeds": FeedsResource(client),
        "blog": BlogResource(client),
        "abandoned_cart": AbandonedCartResource(client),
        "referrals": ReferralsResource(client),
        "api_keys": ApiKeysResource(client),
        "webhooks": WebhooksResource(client),
        "audit_log": AuditLogResource(client),
        "integrations": IntegrationsResource(client),
        "billing": BillingResource(client),
        "uploads": UploadsResource(client),
        "campaigns": CampaignsResource(client),
        "programs": ProgramsResource(client),
        "collaborations": CollaborationsResource(client),
        "insights": InsightsResource(client),
        "channels": ChannelsResource(client),
        "contacts": ContactsResource(client),
        "contact_lists": ContactListsResource(client),
        "broadcasts": BroadcastsResource(client),
        "marketing_campaigns": MarketingCampaignsResource(client),
        "funnels": FunnelsResource(client),
        "inbox": InboxResource(client),
        "audience_segments": AudienceSegmentsResource(client),
        "merchant_profile": MerchantProfileResource(client),
        "creator_profile": CreatorProfileResource(client),
        "affiliator_profile": AffiliatorProfileResource(client),
        "marketplace": MarketplaceResource(client),
        "affiliates": AffiliatesResource(client),
        "kyc": KycResource(client),
        "creator_stats": CreatorStatsResource(client),
        "admin": AdminResource(client),
    }


__all__ = [
    "AbandonedCartResource",
    "AdminResource",
    "AffiliatesResource",
    "AffiliatorProfileResource",
    "ApiKeysResource",
    "AudienceSegmentsResource",
    "AuditLogResource",
    "BillingResource",
    "BlogResource",
    "CampaignsResource",
    "ChannelsResource",
    "CollaborationsResource",
    "ContactListsResource",
    "ContactsResource",
    "CreatorProfileResource",
    "CreatorStatsResource",
    "DiscountCodesResource",
    "FeedsResource",
    "FunnelsResource",
    "InboxResource",
    "InsightsResource",
    "IntegrationsResource",
    "KycResource",
    "BroadcastsResource",
    "MarketingCampaignsResource",
    "MarketplaceResource",
    "MerchantProfileResource",
    "PixelsResource",
    "ProgramsResource",
    "ReferralsResource",
    "UploadsResource",
    "WebhooksResource",
    "build_resources",
]
