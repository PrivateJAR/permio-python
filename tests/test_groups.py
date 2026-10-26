"""permio.groups against an in-process gRPC server."""

from __future__ import annotations

from typing import Any

import pytest
from google.protobuf import empty_pb2

from permio import AddMembersResult, Permio, PermioValidationError, RemoveMembersResult
from permio.permissions.v1 import permissions_pb2 as pb

from .conftest import Recorder


def test_create_get_update_delete(client: Permio, rec: Recorder) -> None:
    rec.on("CreateGroup", lambda req, ctx: pb.Group(name=req.name, description=req.description))
    rec.on("GetGroup", lambda req, ctx: pb.Group(name=req.name, principal_id="group:" + req.name))
    rec.on("UpdateGroup", lambda req, ctx: pb.Group(name=req.name, description=req.description))
    rec.on("DeleteGroup", lambda req, ctx: empty_pb2.Empty())

    assert client.groups.create("editors", description="Edits").description == "Edits"
    # Accepts the principal ID form too.
    assert client.groups.get("group:editors").principal_id == "group:editors"
    assert client.groups.update("editors", description="New").description == "New"
    client.groups.delete("editors", project="other")
    assert rec.requests("CreateGroup")[0].project_name == "my-app"
    assert rec.requests("DeleteGroup")[0].project_name == "other"
    assert rec.requests("GetGroup")[0].name == "editors"


def test_members(client: Permio, rec: Recorder) -> None:
    rec.on(
        "AddGroupMembers",
        lambda req, ctx: pb.AddGroupMembersResponse(
            added_principal_ids=["bob"], existing_principal_ids=["alice"]
        ),
    )
    rec.on(
        "RemoveGroupMembers",
        lambda req, ctx: pb.RemoveGroupMembersResponse(
            removed_principal_ids=["bob"], not_member_principal_ids=["carol"]
        ),
    )
    assert client.groups.add_members("eds", ["alice", "bob", "bob"]) == AddMembersResult(
        ["bob"], ["alice"]
    )
    assert list(rec.requests("AddGroupMembers")[0].principal_ids) == ["alice", "bob"]
    assert client.groups.remove_members("eds", ["bob", "carol"]) == RemoveMembersResult(
        ["bob"], ["carol"]
    )


def test_lists(client: Permio, rec: Recorder) -> None:
    def groups(req: Any, ctx: Any) -> Any:
        if not req.pagination.cursor:
            res = pb.ListGroupsResponse(groups=[pb.Group(name="a")])
            res.pagination.next_cursor = "1"
            return res
        return pb.ListGroupsResponse(groups=[pb.Group(name="b")])

    rec.on("ListGroups", groups)
    rec.on(
        "ListGroupMembers",
        lambda req, ctx: pb.ListGroupMembersResponse(members=[pb.GroupMember(principal_id="bob")]),
    )
    rec.on(
        "ListGroupsForPrincipal",
        lambda req, ctx: pb.ListGroupsForPrincipalResponse(groups=[pb.Group(name="eds")]),
    )
    assert [g.name for g in client.groups.list(search="x")] == ["a", "b"]
    assert [m.principal_id for m in client.groups.list_members("eds")] == ["bob"]
    assert [g.name for g in client.groups.list_for_principal("bob")] == ["eds"]
    assert rec.requests("ListGroupsForPrincipal")[0].principal_id == "bob"


def test_validation(client: Permio, rec: Recorder) -> None:
    with pytest.raises(PermioValidationError, match="invalid group name"):
        client.groups.create("Bad Name")
    with pytest.raises(PermioValidationError, match="groups cannot contain groups"):
        client.groups.add_members("eds", ["group:other"])
    with pytest.raises(PermioValidationError, match="at least one principal"):
        client.groups.add_members("eds", [])
    with pytest.raises(PermioValidationError, match="at most 100"):
        client.groups.remove_members("eds", [f"p{i}" for i in range(101)])
    with pytest.raises(PermioValidationError):
        client.groups.add_members("eds", "alice")
    with pytest.raises(PermioValidationError, match="principal is required"):
        client.groups.list_for_principal("")
    assert rec.calls == []
