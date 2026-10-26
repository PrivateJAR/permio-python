# Changelog

All notable changes to this package are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the package uses
[semantic versioning](https://semver.org/).

## 0.1.0 (unreleased)

First release of the hand-written SDK, published to PyPI as `permio`
(previously this repository only held generated stubs, installed from GitHub as
`permio-python`).

### Added

- `Permio` (sync) and `AsyncPermio` (asyncio, `grpc.aio`) clients with the same
  surface: `check`, `check_all`, `check_any`, `check_detailed`,
  `assert_allowed`, `batch_check`, `batch_check_detailed`, `list_access`,
  `who_has_access`, `grant`, `revoke`, `who_am_i`, and paginated
  `list_permissions`, `list_roles`, `list_principals`, `list_assignments`.
- `permio.groups`: create, get, update, delete, list, add/remove members,
  list members, list a principal's groups. `group()` builds `group:<slug>`.
- `resource()` / `encode_segment()` / `assert_resource_uri()` helpers and
  `AccessScopes` (`allows`, `to_prefixes`, `patterns`, `to_regex`).
- Local API key validation (`validate_api_key`), typed errors
  (`PermioError` and subclasses, including `PermioRateLimitError` with
  `retry_after`), per-attempt timeouts, and retries with jittered backoff for
  idempotent reads only; rate-limited reads honour `RetryInfo` / `retry-after`.
- `permio.permissions` / `permio.organisations`: the generated stubs with auth,
  timeouts, retries and typed errors; `permio.raw` re-exports the generated
  modules.
- Apache-2.0 licence, unit tests against an in-process gRPC server, a live
  integration suite, CI on Blacksmith and a PyPI trusted-publishing release
  workflow.

### Changed

- The distribution is now named `permio` (was `permio-python`). The generated
  modules keep their import paths (`permio.permissions.v1`, ...).
