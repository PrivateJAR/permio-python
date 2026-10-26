# permio

Python SDK for [perms.io](https://perms.io), permissions as a service with
hierarchical resource-URI RBAC.

- One call to ask "may this principal do X on this resource?"
- Batch checks, grant and revoke, groups, and "where can they do X?" queries that turn into database filters
- Sync (`Permio`) and asyncio (`AsyncPermio`) clients with the same surface
- Typed errors, retries for idempotent reads, iterators over list endpoints, fully typed (`py.typed`)
- The full generated gRPC API (every RPC of `PermissionsService` and `OrganisationService`) as an escape hatch
- Python 3.9+, over gRPC (`grpcio`)

## Install

```bash
pip install permio
```

## Quick start

Create an API key in the [dashboard](https://perms.io) (keys look like `perms_`
followed by 38 letters and digits), create a permission such as `docs.read`,
and grant it to a principal such as `alice` on `/docs/42` (or from code with
`permio.grant()`). Principal IDs are your own identifiers: user IDs, service
names, anything stable.

```python
from permio import Permio, resource

permio = Permio(project="my-app")  # API key from $PERMIO_API_KEY
if permio.check("alice", "docs.read", resource("docs", "42")):
    print("alice may read doc 42")
```

The same with asyncio:

```python
from permio import AsyncPermio, resource

async with AsyncPermio(project="my-app") as permio:
    allowed = await permio.check("alice", "docs.read", resource("docs", "42"))
```

Both clients are context managers; `close()` (or `await close()`) closes the
gRPC channel. Create one client per process and share it.

`AsyncPermio` opens its channel on first use, inside the running event loop, so
it can be created at module level and used from `asyncio.run(main())`. A
channel belongs to one event loop: to use the same client from a later loop
(another `asyncio.run()`), `await close()` it (or leave an `async with` block)
first; otherwise the call raises `PermioConfigError`.

## Configuration

```python
from permio import DEV_BASE_URL, Permio, RetryOptions

permio = Permio(
    api_key="perms_...",       # default: $PERMIO_API_KEY; checked locally for typos
    base_url=DEV_BASE_URL,     # default: DEFAULT_BASE_URL (https://api.perms.io, production)
    project="my-app",          # default project for every call; each call can pass project=
    timeout=10,                # seconds per attempt; 0 disables
    retries=RetryOptions(max_retries=2, base_delay=0.1, max_delay=2.0),  # or an int
)
```

| Option            | Default                     | Notes |
| ----------------- | --------------------------- | ----- |
| `api_key`         | `$PERMIO_API_KEY`           | A malformed key raises `PermioConfigError` before any request |
| `base_url`        | `https://api.perms.io`      | `https://host[:port]`, `http://host:port` (plaintext, e.g. local) or `host:port` (TLS) |
| `project`         | none                        | Required by every call except `who_am_i()`, here or per call |
| `timeout`         | `10`                        | Per attempt, in seconds. Per-call `timeout=` is an overall deadline across retries |
| `retries`         | `2`                         | `int` or `RetryOptions`; see [Retries and timeouts](#retries-and-timeouts) |
| `channel`         | none                        | Your own `grpc.Channel` (`grpc.aio.Channel` for `AsyncPermio`); not closed by the client |
| `channel_options` | none                        | Extra gRPC channel options when the client creates the channel |

Every call also accepts `metadata=[("header", "value")]` for extra request headers.

### Dev vs prod

`DEFAULT_BASE_URL` (`https://api.perms.io`) is production and the default.
`DEV_BASE_URL` (`https://dev-api.perms.io`) is the development API; keys are
per environment. `permio.who_am_i()` tells you which organisation and project a
key belongs to and whether it can write:

```python
me = permio.who_am_i()
print(me.kind, me.project, me.api_key_access)  # "api_key", "my-app", "full" (or "check")
```

## Checking permissions

`permission` and `resource` take one value or a list (up to 100 each). Every
permission must hold on every resource.

```python
permio.check("alice", "docs.read", "/docs/42")                     # -> bool
permio.check("alice", ["docs.read", "docs.write"], "/docs/42")     # both
permio.check_all("alice", ["docs.read", "docs.write"], "/docs/42") # alias of check
permio.check_any("alice", ["docs.read", "docs.admin"], "/docs/42") # at least one, per resource

result = permio.check_detailed("alice", ["docs.read", "docs.write"], "/docs/42")
result.allowed   # bool
result.missing   # [MissingPermission(resource="/docs/42", permissions=["docs.write"])]

permio.assert_allowed("alice", "docs.write", "/docs/42")  # raises PermioDeniedError if not
```

A denial is an answer, not an error: `check()` returns `False`.
(`assert` is a Python keyword, so the raising variant is `assert_allowed`.)

### Resource URIs

Grants on a URI apply to everything below it: `/docs` covers `/docs/42`. A `_`
segment in a stored grant matches exactly one segment. Build URIs with
`resource()`, which percent-encodes each segment so IDs containing `/` or
spaces stay one segment:

```python
from permio import resource

resource("projects", project_id, "docs", doc_id)  # "/projects/p1/docs/a%2Fb"
```

Build URIs the same way when granting and when checking. `assert_resource_uri()`
checks the basic shape (leading `/`, no empty segments, no whitespace, at most
2048 bytes); the SDK runs it before sending.

## Batch checks

Check many resources at once; each is answered separately. More than 100 are
split into several `BatchCheck` calls (`AsyncPermio` sends up to 4 at once).

```python
allowed = permio.batch_check("alice", "docs.read", [resource("docs", d.id) for d in docs])
visible = [d for d in docs if allowed[resource("docs", d.id)]]

for entry in permio.batch_check_detailed("alice", ["docs.read", "docs.write"], uris):
    print(entry.resource, entry.allowed, entry.missing)
```

## Granting and revoking

Needs a full-access API key.

```python
permio.grant("alice", "/docs/42", permissions="docs.read")
permio.grant("alice", "/docs", permissions=["docs.read", "docs.write"], roles="role-id")
permio.revoke("alice", "/docs/42", permissions="docs.read")
```

Grants are additive. `revoke` removes names from the grant on exactly that URI
(grants on ancestor URIs stay, so `check()` may still pass) and ignores names
the grant lacks, so revoking twice is harmless. Roles are referenced by ID
(`permio.list_roles()`). Neither call is ever retried automatically.

## Groups

A group is the principal `group:<slug>`; grant to it and every member holds
the grant. Groups cannot contain groups. Methods accept the slug or the
`group:` form.

```python
from permio import group

permio.groups.create("editors", description="Can edit docs")
permio.groups.add_members("editors", ["alice", "bob"])     # AddMembersResult(added, existing)
permio.grant(group("editors"), "/docs", permissions="docs.write")
permio.check("bob", "docs.write", "/docs/42")              # True, through the group

permio.groups.get("editors")
permio.groups.update("editors", description="Edits docs")
for g in permio.groups.list(search="edit"): ...
for m in permio.groups.list_members("editors"): print(m.principal_id)
for g in permio.groups.list_for_principal("bob"): print(g.name)
permio.groups.remove_members("editors", ["bob"])          # RemoveMembersResult(removed, not_members)
permio.groups.delete("editors")                           # also removes its grants
```

## Filtering lists ("where can they do X?")

`list_access` returns where a principal holds a permission at or below a URI,
following every page, so you can filter in your database instead of checking
row by row:

```python
access = permio.list_access("alice", "docs.read", "/docs")
if access.covers_all:
    rows = all_docs()                       # no filter needed
else:
    prefixes = access.to_prefixes()          # ["/docs/1", "/docs/7"]
    regex = access.to_regex().pattern        # for PostgreSQL ~ or MongoDB $regex (covers _ patterns too)
visible = [d for d in docs if access.allows(d.uri)]
```

A prefix `p` stands for `p` itself and everything below it. Match it with a
literal prefix test, for example in PostgreSQL:

```sql
WHERE path = :p OR starts_with(path, :p || '/')
```

Don't use `path LIKE p || '/%'`: `_` and `%` are wildcards in `LIKE`, so a
prefix such as `/docs/a_b` would also match `/docs/axb/...` (and `_` is common
in IDs). If your database has no `starts_with`, compare
`left(path, length(:p) + 1) = :p || '/'` instead, or escape `\`, `%` and `_` in
`p` and add an `ESCAPE` clause. A bare prefix test without the `/` would also
match `/docs/12` for `/docs/1`.

## Who has access

```python
for entry in permio.who_has_access("/docs/42", permission="docs.read", expand_groups=True):
    print(entry.principal, entry.is_group, entry.via_group,
          [(g.resource, g.match, g.source.type) for g in entry.via])
```

## Listing

List helpers return iterators (async iterators on `AsyncPermio`) that fetch
pages of up to 100 items as you go. If the API ever repeats a page cursor, the
iterator raises `PermioError` rather than looping or stopping early:

```python
for p in permio.list_permissions(search="docs."): print(p.name)
for role in permio.list_roles(): print(role.id, role.name)
for principal_id in permio.list_principals(): print(principal_id)
for a in permio.list_assignments("alice"): print(a.resource_uri, a.roles)

async for p in async_permio.list_permissions(): ...
```

`page_size=` (1..100) sets the page size. Items are the generated protobuf
messages (`permio.raw.permissions_pb2.Permission`, `Role`, `Group`, ...).

## Errors

Every error extends `PermioError`, which has `code` (a `grpc.StatusCode`, or
None for SDK-side errors), `code_name` (for example `"permission_denied"`),
`message` and `metadata` (response headers and trailers). The original
`grpc.RpcError` is chained as `__cause__`.

| Class                    | When |
| ------------------------ | ---- |
| `PermioConfigError`      | Bad client setup: malformed or missing API key, no `project`, invalid `base_url` |
| `PermioAuthError`        | `UNAUTHENTICATED`: the key is unknown, invalidated or missing |
| `PermioPermissionError`  | `PERMISSION_DENIED`: the *API key* lacks rights for this call. `missing` lists what it lacks when the API says |
| `PermioValidationError`  | `INVALID_ARGUMENT`, or the SDK's own input checks (e.g. a URI without a leading `/`) |
| `PermioNotFoundError`    | `NOT_FOUND`, e.g. `groups.get()` for a group that does not exist |
| `PermioUnavailableError` | `UNAVAILABLE`, including network failures |
| `PermioTimeoutError`     | `DEADLINE_EXCEEDED`, including the SDK's own deadlines |
| `PermioRateLimitError`   | `RESOURCE_EXHAUSTED`: the organisation's rate limit is used up. `retry_after` is the server's requested delay in seconds (or None) |
| `PermioDeniedError`      | Raised only by `assert_allowed()` when the *principal* is not allowed; has `principal` and `missing` |

Anything else is a plain `PermioError` with the matching `code`.

```python
from permio import PermioAuthError, PermioDeniedError, PermioError, PermioPermissionError

try:
    permio.assert_allowed(user_id, "docs.write", resource("docs", doc_id))
except PermioDeniedError:
    ...  # the principal may not do this: return 403
except PermioPermissionError as err:
    print(err.missing)  # the API key may not check this (needs permission.check)
except PermioAuthError:
    ...  # rotate or fix the API key
except PermioError as err:
    print(err.code_name, err.message)
```

`PermioPermissionError.missing` uses the API's fully qualified URIs
(`/organisation/{org}/project/{project}/...`), not the URIs you sent.

### Retries and timeouts

Idempotent reads (`Check`, `BatchCheck`, `WhoAmI`, and every `Get*` and `List*`
RPC; see `is_idempotent_method()`) are retried on `UNAVAILABLE` and
`DEADLINE_EXCEEDED`, twice by default, with exponential backoff and jitter.
Writes, including `grant` and `revoke`, are never retried: after a timeout the
first attempt may still have landed.

Rate limiting: when the API answers `RESOURCE_EXHAUSTED` with a
`google.rpc.RetryInfo` delay or a `retry-after` header, an idempotent read is
retried after that delay (plus a little jitter) if it is within
`RetryOptions.max_delay`; otherwise `PermioRateLimitError` is raised with
`retry_after`. A `retry-after` header on `UNAVAILABLE` is honoured as the
minimum backoff.

`timeout` on the client applies to each attempt; `timeout=` on a call is an
overall deadline across retries. On `AsyncPermio`, cancelling the task cancels
the call and any pending retry.

## Raw clients (full API)

Everything not wrapped above (permission and role CRUD, organisations,
projects, API keys, usage, ...) is reachable through the generated stubs.
`permio.permissions` and `permio.organisations` are the generated
`PermissionsService` / `OrganisationService` stubs with auth, timeouts,
retries (reads only) and typed errors applied; the messages live in
`permio.raw`:

```python
from permio import raw

pb = raw.permissions_pb2
permio.permissions.CreatePermission(pb.CreatePermissionRequest(project_name="my-app", name="docs.read"))
role = permio.permissions.CreateRole(
    pb.CreateRoleRequest(project_name="my-app", name="Reader", permissions=["docs.read"])
)
project = permio.organisations.GetProject(raw.organisation_pb2.GetProjectRequest(project_name="my-app"))
```

On `AsyncPermio` these methods are coroutines. For the bare stubs with no SDK
behaviour, use `raw.permissions_pb2_grpc.PermissionsServiceStub(channel)` with
your own channel and `authorization: Bearer <key>` metadata.

The generated modules are `permio.permissions.v1`, `permio.organisation.v1`,
`permio.pagination.v1` and `permio.validate`. They are produced from
[PrivateJAR/proto](https://github.com/PrivateJAR/proto) and must not be edited
by hand.

## API key format

`perms_` keys are 44 characters: `perms_`, 32 base62 characters and a 6
character base62 CRC32 checksum. The client checks the format and checksum
locally (`validate_api_key()`, `is_valid_api_key()`) so a mistyped key fails
fast with `PermioConfigError`. Legacy JWT keys are accepted by shape. Only the
API can tell whether a key exists and is still valid.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests && ruff format --check src tests
mypy                  # strict, on the hand-written package only
pytest                # unit tests against an in-process gRPC server
```

### Integration tests

`tests/test_live.py` runs the same scenarios as the other Permio SDKs against a
real deployment: whoAmI, grant then check, batch check, list access, revoke,
groups, and a bad key. It is skipped unless `PERMIO_API_KEY` is set, defaults
to the dev API (`PERMIO_BASE_URL` overrides it) and refuses to run against
production. The key needs full access to its project (`PERMIO_PROJECT`, default
the key's own project). It creates and deletes fixed `sdk-it-python-*` IDs.

```bash
PERMIO_API_KEY=perms_... pytest tests/test_live.py -v
```

CI runs it in a serialised `integration` job when the `PERMIO_DEV_API_KEY`
repository secret exists, and skips it with a notice otherwise.

### Releasing

`.github/workflows/release.yml` runs on `v*` tags: it checks the tag matches
`src/permio/_version.py`, runs the tests, builds the sdist and wheel and
publishes them to PyPI with [trusted publishing](https://docs.pypi.org/trusted-publishers/)
(no API token). The trusted publisher is registered on PyPI for the project
`permio` (owner `PrivateJAR`, repository `permio-python`, workflow
`release.yml`, environment `pypi`), so pushing a tag that matches the version
is all a release needs. Every CI job runs on Blacksmith except the publish step,
which runs on a GitHub-hosted runner because `pypa/gh-action-pypi-publish` only
supports self-hosted runners on a best-effort basis.

## License

[Apache-2.0](LICENSE). Copyright PrivateJAR.
