"""Pure helpers: API key format, resource URIs, groups, access scopes, error parsing."""

from __future__ import annotations

import re
import zlib

import pytest

from permio import (
    API_KEY_LENGTH,
    AccessScopeInfo,
    AccessScopes,
    MissingPermission,
    Permio,
    PermioConfigError,
    PermioValidationError,
    assert_resource_uri,
    encode_segment,
    group,
    is_idempotent_method,
    is_valid_api_key,
    parse_missing_permissions,
    resource,
    validate_api_key,
)
from permio._errors import server_retry_delay
from permio._transport import parse_target

from .conftest import VALID_KEY

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def make_key(body: str) -> str:
    value = zlib.crc32(body.encode()) & 0xFFFFFFFF
    out = ""
    for _ in range(6):
        value, rem = divmod(value, 62)
        out = ALPHABET[rem] + out
    return "perms_" + body + out


class TestApiKey:
    def test_valid_opaque_key(self) -> None:
        assert len(VALID_KEY) == API_KEY_LENGTH == 44
        assert validate_api_key(VALID_KEY) == "opaque"
        assert validate_api_key(make_key("a" * 32)) == "opaque"
        assert is_valid_api_key(VALID_KEY)

    def test_jwt_shape(self) -> None:
        assert validate_api_key("aaa.bbb.ccc") == "jwt"

    @pytest.mark.parametrize(
        ("key", "message"),
        [
            ("", "required"),
            (None, "required"),
            ("perms_short", "expected 44 characters"),
            ("perms_" + "!" * 38, "must be 0-9, A-Z or a-z"),
            (VALID_KEY[:-1] + ("M" if VALID_KEY[-1] != "M" else "N"), "checksum mismatch"),
            ("not-a-key", "malformed API key"),
        ],
    )
    def test_rejects(self, key: object, message: str) -> None:
        with pytest.raises(PermioConfigError, match=message):
            validate_api_key(key)
        assert not is_valid_api_key(key)

    @pytest.mark.parametrize(
        "key",
        [
            VALID_KEY + "\n",
            VALID_KEY + "\r\n",
            " " + VALID_KEY,
            "\t" + VALID_KEY + " ",
            "aaa.bbb.ccc\n",
            " aaa.bbb.ccc",
        ],
    )
    def test_rejects_surrounding_whitespace(self, key: str) -> None:
        # Not stripped silently: a newline from a file or secret is a config error.
        with pytest.raises(PermioConfigError, match="whitespace"):
            validate_api_key(key)
        assert not is_valid_api_key(key)

    def test_jwt_rejects_trailing_newline_and_extra_parts(self) -> None:
        for key in ["aaa.bbb.ccc.ddd", "aaa.bbb", "aaa.bbb.c\nc"]:
            assert not is_valid_api_key(key)

    def test_client_validates_key_and_reads_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with pytest.raises(PermioConfigError):
            Permio("perms_typo", base_url="http://127.0.0.1:1")
        monkeypatch.delenv("PERMIO_API_KEY", raising=False)
        with pytest.raises(PermioConfigError, match="PERMIO_API_KEY"):
            Permio(base_url="http://127.0.0.1:1")
        monkeypatch.setenv("PERMIO_API_KEY", VALID_KEY)
        with Permio(base_url="http://127.0.0.1:1") as p:
            assert p.api_key_kind == "opaque"


class TestResource:
    def test_encodes_segments(self) -> None:
        assert resource("projects", "p1", "docs", "a/b") == "/projects/p1/docs/a%2Fb"
        assert resource("docs", 42) == "/docs/42"
        assert resource("x", "a b!'()*~-_.") == "/x/a%20b%21%27%28%29%2A~-_."
        assert encode_segment("é") == "%C3%A9"

    def test_rejects_empty(self) -> None:
        with pytest.raises(PermioValidationError):
            resource()
        with pytest.raises(PermioValidationError):
            resource("docs", "")

    @pytest.mark.parametrize(
        ("uri", "why"),
        [
            ("", "empty"),
            ("docs/1", 'start with "/"'),
            ("/docs//1", "empty segment"),
            ("/docs/", "empty segment"),
            ("/docs/a b", "whitespace"),
            ("/docs/\x01", "control"),
            ("/" + "a" * 2048, "longer than 2048"),
        ],
    )
    def test_assert_resource_uri(self, uri: str, why: str) -> None:
        with pytest.raises(PermioValidationError, match=why):
            assert_resource_uri(uri)

    def test_valid_uris(self) -> None:
        assert_resource_uri("/docs/1")
        assert_resource_uri("/docs/_/x")

    def test_group(self) -> None:
        assert group("editors") == "group:editors"
        for bad in ["", "Editors", "a_b", "x" * 65, "editors\n", "editors\r\n", " editors"]:
            with pytest.raises(PermioValidationError):
                group(bad)


class TestAccessScopes:
    def scopes(self) -> AccessScopes:
        return AccessScopes(
            "/docs",
            False,
            [
                AccessScopeInfo("/docs/1", "subtree"),
                AccessScopeInfo("/docs/1/sub", "subtree"),
                AccessScopeInfo("/docs/_/shared", "pattern"),
                AccessScopeInfo("/docs/exact", "exact"),
                AccessScopeInfo("/docs/what", "unknown"),
            ],
        )

    def test_allows(self) -> None:
        s = self.scopes()
        assert s.allows("/docs/1")
        assert s.allows("/docs/1/x")
        assert not s.allows("/docs/12")
        assert s.allows("/docs/9/shared")
        assert s.allows("/docs/9/shared/more")
        assert not s.allows("/docs/9")
        assert s.allows("/docs/exact")
        assert not s.allows("/docs/exact/x")
        assert not s.allows("/docs/what")
        assert not s.allows("docs/1")
        assert not s.allows("/docs//1")

    def test_prefixes_patterns_regex(self) -> None:
        s = self.scopes()
        assert s.to_prefixes() == ["/docs/1"]
        assert s.patterns() == ["/docs/_/shared"]
        assert s.exact() == ["/docs/exact"]
        assert s.has_patterns
        assert not s.is_empty
        rx = s.to_regex()
        for uri in ["/docs/1", "/docs/1/x", "/docs/12", "/docs/9/shared", "/docs/9", "/docs/exact"]:
            assert bool(rx.match(uri)) == s.allows(uri), uri

    def test_regex_escapes_like_js(self) -> None:
        s = AccessScopes("/", False, [AccessScopeInfo("/a.b/c+d", "subtree")])
        assert s.to_regex().pattern == r"^(?:\/a\.b\/c\+d(?:\/.*)?)$"

    def test_empty(self) -> None:
        s = AccessScopes("/docs", False, [])
        assert s.is_empty
        assert s.to_regex().match("/docs") is None
        assert re.compile(s.to_regex().pattern).match("") is None


class TestErrorsAndRetryPolicy:
    def test_parse_missing_permissions(self) -> None:
        msg = (
            "missing permissions: [{ResourceURI:/organisation/o/project/p/doc "
            "MissingPermissions:[permission.check principal.get]} "
            "{ResourceURI:/organisation/o/project/p/x MissingPermissions:[]}]"
        )
        assert parse_missing_permissions(msg) == [
            MissingPermission(
                "/organisation/o/project/p/doc", ["permission.check", "principal.get"]
            ),
            MissingPermission("/organisation/o/project/p/x", []),
        ]
        assert parse_missing_permissions("nope") == []

    def test_retry_after_header(self) -> None:
        assert server_retry_delay((("retry-after", "3"),)) == 3.0
        assert server_retry_delay((("retry-after", "soon"),)) is None
        assert server_retry_delay(()) is None
        delay = server_retry_delay((("retry-after", "Wed, 21 Oct 2015 07:28:00 GMT"),))
        assert delay == 0.0

    def test_idempotent_allowlist(self) -> None:
        svc = "permio.permissions.v1.PermissionsService."
        assert is_idempotent_method(svc + "Check")
        assert is_idempotent_method(svc + "WhoAmI")
        assert is_idempotent_method("permio.organisation.v1.OrganisationService.GetProject")
        for write in [
            "GrantUserPermissionsAndRolesOnResource",
            "RevokeUserPermissionsAndRolesOnResource",
            "CreatePermission",
            "DeleteGroup",
            "AddGroupMembers",
        ]:
            assert not is_idempotent_method(svc + write)

    @pytest.mark.parametrize(
        ("url", "target", "secure"),
        [
            ("https://api.perms.io", "api.perms.io:443", True),
            ("https://dev-api.perms.io/", "dev-api.perms.io:443", True),
            ("http://localhost:8080", "localhost:8080", False),
            ("http://localhost", "localhost:80", False),
            ("api.perms.io:443", "api.perms.io:443", True),
            ("api.perms.io", "api.perms.io:443", True),
            ("http://[::1]:9000", "[::1]:9000", False),
        ],
    )
    def test_parse_target(self, url: str, target: str, secure: bool) -> None:
        assert parse_target(url) == (target, secure)

    @pytest.mark.parametrize("url", ["ftp://x", "https://x/path", "", "x/y"])
    def test_parse_target_rejects(self, url: str) -> None:
        with pytest.raises(PermioConfigError):
            parse_target(url)


class TestLiveGuard:
    """tests/test_live.py only runs against the dev API and local/test hosts."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://dev-api.perms.io",
            "https://DEV-API.perms.io:443/",
            "dev-api.perms.io:443",
            "dev-api.perms.io.",
            "http://localhost:8080",
            "http://127.0.0.1:50051",
            "http://[::1]:50051",
            "http://permio.localhost:8080",
            "https://api.permio.test",
        ],
    )
    def test_allows(self, url: str) -> None:
        from .test_live import is_allowed_target

        assert is_allowed_target(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://api.perms.io",
            "https://API.PERMS.IO",
            "HTTPS://api.perms.io:443/",
            "api.perms.io",
            "api.perms.io:443",
            "https://api.perms.io./",
            "https://temp-api.perms.io",
            "https://dev-api.perms.io.evil.com",
            "https://dev-api.perms.io@api.perms.io",
            "https://evil.com\\@dev-api.perms.io",
            "https://localhost.example.com",
            "https://test",
            "https://.test",
            "https://example.com/x.test",
            "",
        ],
    )
    def test_refuses(self, url: str) -> None:
        from .test_live import is_allowed_target

        assert not is_allowed_target(url)
