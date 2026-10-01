# Changelog

## 0.3.0
- Webhooks are delivered: Ripllo now POSTs every event your endpoints subscribe to, signed `Ripllo-Signature: t=…,v1=…` — what `verify_webhook` already checked — with retries (1 min … 12 h), a delivery log and auto-disable for endpoints that keep failing. 29 more event types are emitted (32 in all, with loyalty).
- `webhooks.list_events` takes `status` and `endpoint_id`; new `webhooks.get_event(id)`, `webhooks.retry_event(id)` and `webhooks.list_event_types()`.
- `client.api`: `webhooks_get_events`, `webhooks_events_retry`, `webhooks_event_types` (regenerated).

## 0.2.0
- A route read by id next to its list is named `get` + the list's name: `client.api.affiliates_get_affiliators` (was `client.api.affiliates_affiliators_2`), `client.api.affiliates_get_programs` (was `client.api.affiliates_programs_2`), `client.api.blog_get_public` (was `client.api.blog_public`), `client.api.blog_get_public_2` (was `client.api.blog_public_2`), `client.api.inbox_get_threads` (was `client.api.inbox_threads_2`), `client.api.marketplace_get_campaigns` (was `client.api.marketplace_campaigns_2`), `client.api.marketplace_get_creators` (was `client.api.marketplace_creators_2`). Each old name stays as a deprecated alias.
- Query fields the API refuses a request without are now required: `code` on GET /api/v1/creator-stats/connect/{platform}/callback, `state` on GET /api/v1/creator-stats/connect/{platform}/callback, `key` on GET /api/v1/uploads/avatar, `id` on GET /api/v1/uploads/deliverable, `key` on GET /api/v1/uploads/merchant-asset.

## 0.1.3

- `client.api` regenerated from the API spec: 208 routes.
- Signatures: the API now accepts a request signed over the exact bytes sent, so bodies
  with non-ASCII text (which Python escapes), floats like `1.0` or an empty `{}` no longer
  fail with `BAD_SIGNATURE`.
- `ripllo.__version__` reports the package version (it said 0.1.0).

## 0.1.0
- Initial tracked release.
