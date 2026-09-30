# Changelog

## 0.1.3

- `client.api` regenerated from the API spec: 208 routes.
- Signatures: the API now accepts a request signed over the exact bytes sent, so bodies
  with non-ASCII text (which Python escapes), floats like `1.0` or an empty `{}` no longer
  fail with `BAD_SIGNATURE`.
- `ripllo.__version__` reports the package version (it said 0.1.0).

## 0.1.0
- Initial tracked release.
