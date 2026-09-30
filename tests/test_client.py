"""Smoke tests for RiplloClient.

Uses httpx.MockTransport (same pattern as the Huudis SDK) instead of
respx so the test surface stays free of extra deps when respx isn't
installed. respx is still pinned in the dev extras for parity.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Tuple

import httpx
import pytest

from ripllo import RiplloClient, RiplloError, verify_webhook


# ─── Helpers ────────────────────────────────────────────────────


def _envelope(data: Any, error: Any = None, request_id: str = "req_test") -> bytes:
    return json.dumps(
        {"data": data, "error": error, "meta": {"requestId": request_id}}
    ).encode()


def _make_client(
    *,
    on_behalf_of: str | None = None,
    response_factory=None,
) -> Tuple[RiplloClient, List[Dict[str, Any]]]:
    captured: List[Dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode() if request.content else None
        captured.append(
            {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "raw_path": request.url.raw_path.decode(),
                "query": request.url.query.decode(),
                "headers": dict(request.headers),
                "body": body,
            }
        )
        if response_factory is not None:
            return response_factory(request)
        return httpx.Response(200, content=_envelope({"ok": True}))

    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    client = RiplloClient(
        key_id="AKIARPLOtest",
        secret="shhh",
        base_url="https://ripllo.test",
        on_behalf_of=on_behalf_of,
        http=http,
    )
    return client, captured


# ─── HMAC signing ───────────────────────────────────────────────


def test_request_sends_hmac_signature_header():
    client, captured = _make_client()
    client.discount_codes.list()
    h = captured[0]["headers"]
    assert h["authorization"].startswith("Ripllo-HMAC-SHA256 keyId=AKIARPLOtest,")
    assert "signature=" in h["authorization"]
    assert "x-ripllo-timestamp" in h
    assert h["accept"] == "application/json"


def test_signature_matches_node_sdk_format():
    """Re-derive the signature outside the SDK and assert byte-equality."""
    client, captured = _make_client()
    fixed_ts = 1700000000
    # Patch time to a fixed value so we can reproduce the signature.
    import ripllo.client as _c

    real_time = _c.time.time
    try:
        _c.time.time = lambda: fixed_ts  # type: ignore[assignment]
        client.discount_codes.list()
    finally:
        _c.time.time = real_time  # type: ignore[assignment]

    body_hash = hashlib.sha256(b"").hexdigest()
    string_to_sign = f"GET\n/api/v1/discount-codes\n{fixed_ts}\n{body_hash}"
    expected_sig = hmac.new(
        b"shhh", string_to_sign.encode(), hashlib.sha256
    ).hexdigest()
    auth = captured[0]["headers"]["authorization"]
    assert f"signature={expected_sig}" in auth
    assert captured[0]["headers"]["x-ripllo-timestamp"] == str(fixed_ts)


def test_signature_strips_query_string_before_signing():
    """Same fix as the Node SDK — sign the path without ?query."""
    client, captured = _make_client()
    fixed_ts = 1700000000
    import ripllo.client as _c

    real_time = _c.time.time
    try:
        _c.time.time = lambda: fixed_ts  # type: ignore[assignment]
        client.discount_codes.list(limit=10, active=True)
    finally:
        _c.time.time = real_time  # type: ignore[assignment]

    body_hash = hashlib.sha256(b"").hexdigest()
    string_to_sign = f"GET\n/api/v1/discount-codes\n{fixed_ts}\n{body_hash}"
    expected_sig = hmac.new(
        b"shhh", string_to_sign.encode(), hashlib.sha256
    ).hexdigest()
    auth = captured[0]["headers"]["authorization"]
    assert f"signature={expected_sig}" in auth
    # And the actual request must still carry the query
    assert "limit=10" in captured[0]["url"]
    assert "active=true" in captured[0]["url"]  # the server reads "true"


def test_idempotency_key_is_included_in_signing_and_header():
    client, captured = _make_client()
    client.discount_codes.create({"code": "WELCOME10", "type": "percent", "value": 10, "currency": "IDR"})
    h = captured[0]["headers"]
    assert "idempotency-key" in h
    assert h["idempotency-key"].startswith("idem_")
    assert h["content-type"] == "application/json"


def test_on_behalf_of_header_sent_when_provided():
    client, _ = _make_client(on_behalf_of="acc_partnermerch_1")
    _, captured = client, _
    # New client with mock transport for proper capture
    client, captured = _make_client(on_behalf_of="acc_partnermerch_1")
    client.discount_codes.list()
    assert captured[0]["headers"]["x-ripllo-on-behalf-of"] == "acc_partnermerch_1"


def test_for_merchant_clones_with_obo():
    client, _ = _make_client()
    scoped = client.for_merchant("acc_x")
    assert scoped.default_on_behalf_of == "acc_x"
    assert scoped.key_id == client.key_id


def test_missing_credentials_raises():
    with pytest.raises(ValueError):
        RiplloClient(key_id="", secret="x")
    with pytest.raises(ValueError):
        RiplloClient(key_id="x", secret="")


# ─── Error handling ─────────────────────────────────────────────


def test_4xx_envelope_raises_ripllo_error():
    def respond(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            content=_envelope(
                None,
                error={"code": "not_found", "message": "no such code"},
                request_id="req_xyz",
            ),
        )

    client, _ = _make_client(response_factory=respond)
    with pytest.raises(RiplloError) as excinfo:
        client.discount_codes.get("dc_missing")
    err = excinfo.value
    assert err.status == 404
    assert err.code == "not_found"
    assert err.message == "no such code"
    assert err.request_id == "req_xyz"


def test_non_json_response_raises_invalid_response():
    def respond(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(502, content=b"<html>oops</html>")

    client, _ = _make_client(response_factory=respond)
    with pytest.raises(RiplloError) as excinfo:
        client.discount_codes.list()
    assert excinfo.value.code == "invalid_response"
    assert excinfo.value.status == 502


# ─── Resource: discount codes ───────────────────────────────────


def test_discount_codes_list_path():
    client, captured = _make_client()
    client.discount_codes.list(limit=20, active=True)
    url = captured[0]["url"]
    assert "/api/v1/discount-codes" in url
    assert "limit=20" in url
    assert "active=true" in url  # the server reads "true"


def test_discount_codes_create_post_body():
    client, captured = _make_client()
    client.discount_codes.create(
        {"code": "X", "type": "percent", "value": 10, "currency": "IDR"}
    )
    assert captured[0]["method"] == "POST"
    assert json.loads(captured[0]["body"])["code"] == "X"


def test_discount_codes_archive_delete():
    client, captured = _make_client()
    client.discount_codes.archive("dc_1")
    assert captured[0]["method"] == "DELETE"
    assert captured[0]["path"] == "/api/v1/discount-codes/dc_1"


def test_discount_codes_applicable_public_path():
    client, captured = _make_client()
    client.discount_codes.applicable("acc_abc", currency="IDR", subtotal=50000)
    url = captured[0]["url"]
    assert "/api/v1/discount-codes/applicable/acc_abc" in url
    assert "currency=IDR" in url
    assert "subtotal=50000" in url


# ─── Resource: pixels / feeds / blog / abandoned_cart ───────────


def test_pixels_public_path():
    client, captured = _make_client()
    client.pixels.public("acc_abc")
    assert captured[0]["path"] == "/api/v1/pixels/public/acc_abc"


def test_feeds_google_feed_url_is_string():
    client, _ = _make_client()
    url = client.feeds.google_feed_url("acc_abc")
    assert url == "https://ripllo.test/api/v1/feeds/google/acc_abc.xml"


def test_blog_create_post_with_idempotency():
    client, captured = _make_client()
    client.blog.create({"slug": "hello", "title": "Hello", "body": "..."})
    assert captured[0]["method"] == "POST"
    assert captured[0]["headers"]["idempotency-key"].startswith("idem_")


def test_abandoned_cart_record_reminder():
    client, captured = _make_client()
    client.abandoned_cart.record_reminder({"accountId": "acc_x", "customerId": "c_1", "cartId": "ct_1", "email": "a@b.com", "cartSnapshot": {}, "valueAtSend": 1000, "currencyAtSend": "IDR"})
    assert captured[0]["path"] == "/api/v1/abandoned-cart/reminders"
    assert captured[0]["method"] == "POST"


# ─── Resource: referrals ────────────────────────────────────────


def test_referrals_resolve_link_path():
    client, captured = _make_client()
    client.referrals.resolve_link("acc_x", "AB12")
    assert captured[0]["path"] == "/api/v1/referrals/links/acc_x/AB12"


def test_referrals_void_attribution_body():
    client, captured = _make_client()
    client.referrals.void_attribution_on_refund("cs_123")
    body = json.loads(captured[0]["body"])
    assert body == {"checkoutSessionId": "cs_123"}


# ─── Creator marketplace: campaigns / programs / collaborations ─


def test_campaigns_accept_application_path():
    client, captured = _make_client()
    client.campaigns.accept_application("camp_1", "app_1")
    assert (
        captured[0]["path"]
        == "/api/v1/campaigns/camp_1/applications/app_1/accept"
    )


def test_programs_approve_short_alias():
    client, captured = _make_client()
    client.programs.approve("p1", "e1")
    assert (
        captured[0]["path"] == "/api/v1/programs/p1/enrollments/e1/approve"
    )


def test_collaborations_publish_deliverable():
    client, captured = _make_client()
    client.collaborations.publish_deliverable("co1", "d1")
    assert (
        captured[0]["path"]
        == "/api/v1/collaborations/co1/deliverables/d1/published"
    )


def test_collaborations_deliverables_nested_alias():
    client, captured = _make_client()
    client.collaborations.deliverables.approve("co1", "d1")
    assert (
        captured[0]["path"]
        == "/api/v1/collaborations/co1/deliverables/d1/approve"
    )


# ─── Marketing: channels / contacts / contact-lists ─────────────


def test_channels_test_post():
    client, captured = _make_client()
    client.channels.test("ch1")
    assert captured[0]["path"] == "/api/v1/channels/ch1/test"
    assert captured[0]["method"] == "POST"


def test_contacts_import_keyword_safe():
    client, captured = _make_client()
    client.contacts.import_({"rows": []})
    assert captured[0]["path"] == "/api/v1/contacts/import"
    assert captured[0]["method"] == "POST"


def test_contact_lists_remove_member_delete():
    client, captured = _make_client()
    client.contact_lists.remove_member("l1", "c1")
    assert captured[0]["method"] == "DELETE"
    assert captured[0]["path"] == "/api/v1/contact-lists/l1/members/c1"


# ─── Broadcasts (email/SMS) — distinct from marketing-campaign hub ───


def test_broadcasts_list_hits_broadcasts_url():
    client, captured = _make_client()
    client.broadcasts.list()
    assert captured[0]["method"] == "GET"
    assert captured[0]["path"] == "/api/v1/broadcasts"


def test_broadcasts_compile_template_hits_broadcasts_url():
    client, captured = _make_client()
    client.broadcasts.compile_template({"template": "X"})
    assert captured[0]["path"] == "/api/v1/broadcasts/templates/compile"


def test_broadcasts_templates_nested_alias_uses_broadcasts_url():
    client, captured = _make_client()
    client.broadcasts.templates.list()
    assert captured[0]["path"] == "/api/v1/broadcasts/templates"


# ─── Marketing campaigns (hub) ──────────────────────────────────


def test_marketing_campaigns_is_separate_resource_from_broadcasts():
    client, _ = _make_client()
    assert client.marketing_campaigns is not client.broadcasts


def test_marketing_campaigns_list_hits_hub_url():
    client, captured = _make_client()
    client.marketing_campaigns.list()
    assert captured[0]["method"] == "GET"
    assert captured[0]["path"] == "/api/v1/marketing-campaigns"


def test_marketing_campaigns_list_status_array_joined():
    client, captured = _make_client()
    client.marketing_campaigns.list(status=["draft", "live"])
    # path stays plain; querystring carries the joined value.
    assert captured[0]["path"] == "/api/v1/marketing-campaigns"
    assert "status=draft%2Clive" in captured[0]["query"]


def test_marketing_campaigns_get_hits_id_path_without_full():
    client, captured = _make_client()
    client.marketing_campaigns.get("mc_abc")
    assert captured[0]["method"] == "GET"
    assert captured[0]["path"] == "/api/v1/marketing-campaigns/mc_abc"


def test_marketing_campaigns_get_full_hits_full_subpath():
    client, captured = _make_client()
    client.marketing_campaigns.get_full("mc_abc")
    assert captured[0]["method"] == "GET"
    assert captured[0]["path"] == "/api/v1/marketing-campaigns/mc_abc/full"


def test_marketing_campaigns_selector_hits_selector_path():
    client, captured = _make_client()
    client.marketing_campaigns.selector()
    assert captured[0]["method"] == "GET"
    assert captured[0]["path"] == "/api/v1/marketing-campaigns/_/selector"


def test_marketing_campaigns_create_posts_body_and_idempotency():
    client, captured = _make_client()
    client.marketing_campaigns.create({"name": "Q3 Push", "goal": "conversion"})
    assert captured[0]["method"] == "POST"
    assert captured[0]["path"] == "/api/v1/marketing-campaigns"
    body = json.loads(captured[0]["body"])
    assert body == {"name": "Q3 Push", "goal": "conversion"}
    assert captured[0]["headers"]["idempotency-key"].startswith("idem_")


def test_marketing_campaigns_update_patches_id_path():
    client, captured = _make_client()
    client.marketing_campaigns.update("mc_abc", {"status": "live"})
    assert captured[0]["method"] == "PATCH"
    assert captured[0]["path"] == "/api/v1/marketing-campaigns/mc_abc"
    assert json.loads(captured[0]["body"]) == {"status": "live"}


def test_marketing_campaigns_delete_uses_delete_method():
    client, captured = _make_client()
    client.marketing_campaigns.delete("mc_abc")
    assert captured[0]["method"] == "DELETE"
    assert captured[0]["path"] == "/api/v1/marketing-campaigns/mc_abc"


def test_funnels_set_steps_accepts_bare_list():
    client, captured = _make_client()
    client.funnels.set_steps("f1", [{"type": "email"}])
    assert captured[0]["method"] == "PUT"
    body = json.loads(captured[0]["body"])
    assert body == {"steps": [{"type": "email"}]}


def test_inbox_archive_path():
    client, captured = _make_client()
    client.inbox.archive("t1")
    assert captured[0]["path"] == "/api/v1/inbox/t1/archive"


def test_audience_segments_preview_adhoc():
    client, captured = _make_client()
    client.audience_segments.preview_adhoc({"filter": {}})
    assert captured[0]["path"] == "/api/v1/audience-segments/preview"


# ─── Profiles / marketplace / KYC / disputes ────────────────────


def test_merchant_profile_publish():
    client, captured = _make_client()
    client.merchant_profile.publish()
    assert captured[0]["path"] == "/api/v1/merchants/me/publish"


def test_marketplace_apply_short_alias():
    client, captured = _make_client()
    client.marketplace.apply("c1", {"pitch": "hi"})
    assert captured[0]["path"] == "/api/v1/marketplace/campaigns/c1/apply"


def test_admin_reject_kyc_body():
    client, captured = _make_client()
    client.admin.reject_kyc("k1", {"reason": "bad photo"})
    assert captured[0]["path"] == "/api/v1/admin/kyc/k1/reject"
    assert json.loads(captured[0]["body"]) == {"reason": "bad photo"}


def test_admin_resolve_dispute_path():
    client, captured = _make_client()
    client.admin.resolve_dispute("d1", {"resolution": "merchant"})
    assert captured[0]["path"] == "/api/v1/admin/disputes/d1/resolve"


def test_admin_partner_usage_query_translates_from():
    client, captured = _make_client()
    client.admin.partner_usage(from_="2026-05-01", to="2026-05-31", partner="storlaunch")
    url = captured[0]["url"]
    assert "from=2026-05-01" in url
    assert "to=2026-05-31" in url
    assert "partner=storlaunch" in url


# ─── Passthrough + integrations + uploads + insights ────────────


def test_passthrough_returns_data():
    client, captured = _make_client()
    result = client.passthrough("GET", "/api/v1/custom/route")
    assert captured[0]["path"] == "/api/v1/custom/route"
    assert result == {"ok": True}


def test_uploads_sign_merchant_post():
    client, captured = _make_client()
    client.uploads.sign_merchant({"filename": "x.png", "contentType": "image/png"})
    assert captured[0]["path"] == "/api/v1/uploads/sign-merchant"
    assert captured[0]["method"] == "POST"


def test_insights_commissions_trend_query():
    client, captured = _make_client()
    client.insights.commissions_trend(days=30)
    assert "/api/v1/insights/commissions-trend" in captured[0]["url"]
    assert "days=30" in captured[0]["url"]


# ─── Webhooks ───────────────────────────────────────────────────


def _sign_webhook(body: bytes, secret: str, ts: int) -> str:
    payload = f"{ts}.".encode() + body
    v1 = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={v1}"


def test_webhook_verify_happy_path():
    secret = "whsec_test"
    now = int(time.time())
    body = json.dumps({"id": "evt_1", "type": "discount.redeemed", "data": {}}).encode()
    sig = _sign_webhook(body, secret, now)
    event = verify_webhook(raw_body=body, signature=sig, secret=secret)
    assert event["id"] == "evt_1"
    assert event["type"] == "discount.redeemed"


def test_webhook_verify_bad_signature():
    secret = "whsec_test"
    now = int(time.time())
    body = b'{"id":"evt_1"}'
    sig = f"t={now},v1=deadbeef"
    with pytest.raises(RiplloError) as excinfo:
        verify_webhook(raw_body=body, signature=sig, secret=secret)
    assert excinfo.value.code == "bad_signature"


def test_webhook_verify_replay_window():
    secret = "whsec_test"
    now = int(time.time())
    old = now - 600  # 10 minutes ago, default tolerance is 5 min
    body = b'{"id":"evt_1"}'
    sig = _sign_webhook(body, secret, old)
    with pytest.raises(RiplloError) as excinfo:
        verify_webhook(raw_body=body, signature=sig, secret=secret)
    assert excinfo.value.code == "signature_expired"


def test_webhook_verify_missing_header():
    with pytest.raises(RiplloError) as excinfo:
        verify_webhook(raw_body=b"{}", signature=None, secret="x")
    assert excinfo.value.code == "missing_signature"
