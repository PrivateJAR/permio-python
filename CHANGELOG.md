# Changelog

All notable changes to this package are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the package uses
[semantic versioning](https://semver.org/).

## 0.2.0 (unreleased)

### Changed

- **Behaviour change:** `who_has_access` and `list_access` (sync and async)
  collect at most `max_results` items, default 10,000. Past that they raise the
  new `PermioTooManyResultsError` instead of reading every page into memory;
  at most `max_results + 1` items are fetched (the last page request asks only
  for what is still wanted). Pass a larger `max_results` or use the new
  streaming forms. A non-positive `max_results` is a `PermioValidationError`.
- **Behaviour change:** `batch_check` / `batch_check_detailed` accept at most
  `max_resources` resources per call, default 10,000 (counted as given, before
  de-duplication; a generator is read only up to the cap). More raise
  `PermioValidationError` before any request is sent.
- `batch_check` builds each `BatchCheck` request only when it is sent instead
  of all of them up front. `AsyncPermio` runs 4 workers over the chunks:
  results keep request order, and the first error cancels the in-flight
  chunks, sends no more and is raised.

### Added

- `Permio.iter_who_has_access` / `iter_list_access` (iterators) and the
  `AsyncPermio` equivalents (async iterators) stream access listings one page
  at a time. Arguments are validated when called.
- `list_timeout` client option: the per-attempt timeout for every page a list
  helper fetches (iterators, `iter_*`, `who_has_access`, `list_access`,
  `groups.list*`). Defaults to `timeout`.
- `DEFAULT_MAX_RESULTS` and `DEFAULT_MAX_BATCH_RESOURCES` constants.

## 0.1.1

### Fixed

- `AsyncPermio` no longer creates its gRPC channel in the constructor. The
  channel is opened on first use (or by `async with`) inside the running event
  loop, so a client constructed at module level works with `asyncio.run()`
  (previously "attached to a different loop", or "There is no current event
  loop" on Python 3.13). `close()` is safe on a client that never made a call
  and can be called twice; after `close()` the client can be used again from a
  new loop. Using it from a second loop without closing it first raises
  `PermioConfigError` with an explanation. `AsyncPermio.channel` is now a
  property and raises `PermioConfigError` when read outside a running loop
  before the channel is open.
- `check_any` failed open: a denied `Check` response with no missing
  permissions listed returned `True`. It now returns `False`.
- API keys with leading or trailing whitespace (such as a newline read from a
  file) are rejected with a `PermioConfigError` that says so, instead of a
  legacy JWT key with a trailing newline being accepted. Group slugs with a
  trailing newline are rejected too (`fullmatch` instead of `^...$`).
- A listing whose API response repeats a pagination cursor now raises
  `PermioError` instead of silently stopping with partial results.
- `AsyncPermio.batch_check` / `batch_check_detailed` send at most 4
  `BatchCheck` calls (of 100 resources each) at once instead of all of them.

### Changed

- The README and `AccessScopes.to_prefixes()` docs recommend a literal prefix
  test (`starts_with(path, p || '/')`) instead of `LIKE p || '/%'`, in which
  `_` and `%` are wildcards.
- The live test suite only runs against an allowlist of hosts
  (`dev-api.perms.io`, `localhost`, `127.0.0.1`, `::1`, `*.localhost`,
  `*.test`), parsed from the URL, instead of a case-sensitive production
  pattern.

## 0.1.0 (2026-10-26)

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
