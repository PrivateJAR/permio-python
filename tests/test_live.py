"""Integration test against a real deployment.

Skipped unless PERMIO_API_KEY is set. PERMIO_BASE_URL defaults to the
development API (DEV_BASE_URL), and the test refuses to run against production
because it writes. The key needs full access to its project (PERMIO_PROJECT,
default: the key's project from who_am_i)::

    PERMIO_API_KEY=perms_... pytest tests/test_live.py

Everything it creates uses fixed IDs prefixed "sdk-it-python" and is removed
before and after the run, so an interrupted run is cleaned up by the next one.
Runs sharing a project must not overlap (CI serialises them).
"""

from __future__ import annotations

import contextlib
import os
import re
from typing import Iterator

import pytest

from permio import (
    DEV_BASE_URL,
    AsyncPermio,
    Permio,
    PermioAuthError,
    PermioNotFoundError,
    group,
    raw,
)

API_KEY = os.environ.get("PERMIO_API_KEY", "")
BASE_URL = os.environ.get("PERMIO_BASE_URL") or DEV_BASE_URL


def is_prod(url: str) -> bool:
    return bool(re.match(r"^(https?://)?(temp-)?api\.perms\.io(:443)?/?$", url.strip()))


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not API_KEY, reason="PERMIO_API_KEY is not set"),
    pytest.mark.skipif(
        is_prod(BASE_URL), reason="refusing to run the live test against production"
    ),
]

ALICE = "sdk-it-python-alice"
BOB = "sdk-it-python-bob"
GROUP = "sdk-it-python-editors"
READ = "sdk-it-python.read"
WRITE = "sdk-it-python.write"
ROOT = "/sdk-it-python"
DOCS = f"{ROOT}/docs"
DOC1 = f"{DOCS}/1"
OTHER = f"{ROOT}/other"


def clean_up(permio: Permio, project: str) -> None:
    # Deleting the permissions also removes every grant that uses them.
    permio.groups.delete(GROUP)
    for name in (READ, WRITE):
        with contextlib.suppress(PermioNotFoundError):
            permio.permissions.DeletePermission(
                raw.permissions_pb2.DeletePermissionRequest(project_name=project, name=name)
            )


@pytest.fixture(scope="module")
def project() -> str:
    explicit = os.environ.get("PERMIO_PROJECT")
    if explicit:
        return explicit
    with Permio(API_KEY, base_url=BASE_URL) as probe:
        return probe.who_am_i().project or "default"


@pytest.fixture(scope="module")
def permio(project: str) -> Iterator[Permio]:
    with Permio(API_KEY, base_url=BASE_URL, project=project, timeout=30) as client:
        clean_up(client, project)
        for name in (READ, WRITE):
            client.permissions.CreatePermission(
                raw.permissions_pb2.CreatePermissionRequest(
                    project_name=project, name=name, description="permio-python integration test"
                )
            )
        try:
            yield client
        finally:
            clean_up(client, project)


def test_who_am_i_describes_the_api_key(permio: Permio, project: str) -> None:
    me = permio.who_am_i()
    assert me.kind == "api_key"
    assert me.project == project
    assert me.principal_id
    assert me.organisation_id
    assert me.api_key_access == "full"


def test_grant_then_check_is_allowed_below_the_granted_uri(permio: Permio) -> None:
    assert permio.check(ALICE, READ, DOC1) is False
    permio.grant(ALICE, DOCS, permissions=READ)
    assert permio.check(ALICE, READ, DOC1) is True
    assert permio.check(ALICE, WRITE, DOC1) is False


def test_batch_check_answers_each_resource(permio: Permio) -> None:
    result = permio.batch_check(ALICE, READ, [DOC1, OTHER, DOCS])
    assert list(result.items()) == [(DOC1, True), (OTHER, False), (DOCS, True)]


def test_list_access_returns_the_granted_subtree(permio: Permio) -> None:
    access = permio.list_access(ALICE, READ, ROOT)
    assert access.covers_all is False
    assert access.to_prefixes() == [DOCS]
    assert access.allows(DOC1)
    assert not access.allows(OTHER)


async def test_async_client_sees_the_same_grant(project: str) -> None:
    async with AsyncPermio(API_KEY, base_url=BASE_URL, project=project, timeout=30) as client:
        assert await client.check(ALICE, READ, DOC1) is True
        assert [e.principal for e in await client.who_has_access(DOC1, permission=READ)] == [ALICE]


def test_revoke_then_check_is_denied(permio: Permio) -> None:
    permio.revoke(ALICE, DOCS, permissions=READ)
    assert permio.check(ALICE, READ, DOC1) is False
    # Revoking what is no longer held is harmless.
    permio.revoke(ALICE, DOCS, permissions=READ)


def test_group_grant_applies_to_members_until_the_group_is_deleted(permio: Permio) -> None:
    permio.groups.create(GROUP, description="permio-python integration test")
    added = permio.groups.add_members(GROUP, [BOB])
    assert (added.added, added.existing) == ([BOB], [])
    permio.grant(group(GROUP), DOCS, permissions=WRITE)
    assert permio.check(BOB, WRITE, DOC1) is True
    assert permio.check(ALICE, WRITE, DOC1) is False

    permio.groups.delete(GROUP)
    assert permio.check(BOB, WRITE, DOC1) is False


def test_unknown_key_raises_auth_error(project: str) -> None:
    with Permio(
        "perms_0123456789ABCDEFGHIJKLMNOPQRSTUV1ggZdL", base_url=BASE_URL, project=project
    ) as bad:
        with pytest.raises(PermioAuthError):
            bad.check(ALICE, READ, DOC1)
        with pytest.raises(PermioAuthError):
            bad.who_am_i()
