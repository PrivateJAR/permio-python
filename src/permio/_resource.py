"""Resource URI and group principal helpers."""

from __future__ import annotations

import re
from typing import Union
from urllib.parse import quote

from ._errors import PermioValidationError

MAX_RESOURCE_URI_LENGTH = 2048
"""The API rejects resource URIs longer than this many bytes."""

GROUP_PRINCIPAL_PREFIX = "group:"
"""Prefix of the principal ID that grants to a group are made to."""

_SLUG = re.compile(r"[a-z0-9-]{1,64}")
# Whitespace (Python's \s is Unicode-aware; add the BOM, which JavaScript's \s
# also covers) and C0/C1 control characters.
_BAD_CHARS = re.compile("[\\s﻿\u0000-\u001f\u007f-\u009f]")


def encode_segment(segment: Union[str, int]) -> str:
    """Percent-encodes one resource URI segment.

    Everything except ``A-Z a-z 0-9 - _ . ~`` is encoded (UTF-8), so ``/``,
    spaces and the characters the API rejects in segments (``( ) *``) never
    split or break a segment. Matches the JavaScript SDK byte for byte.
    """
    text = str(segment)
    if text == "":
        raise PermioValidationError("permio: resource URI segments must not be empty")
    return quote(text, safe="-_.~")


def resource(*segments: Union[str, int]) -> str:
    """Builds a resource URI from raw segments, encoding each one.

    IDs containing ``/``, spaces or other reserved characters stay a single
    segment::

        resource("projects", project_id, "docs", doc_id)  # "/projects/p1/docs/a%2Fb"

    Build URIs the same way when granting and when checking, or they will not match.
    """
    if not segments:
        raise PermioValidationError("permio: resource() needs at least one segment")
    return "/" + "/".join(encode_segment(s) for s in segments)


def assert_resource_uri(uri: object) -> None:
    """Raises :class:`PermioValidationError` unless ``uri`` has the basic shape the API accepts.

    That is: a leading ``/``, no empty segments (so no ``//`` or trailing ``/``),
    no whitespace or control characters, at most 2048 bytes. The API applies
    further rules (for example no regex metacharacters such as ``( ) [ ] * + ?``
    in segments) and answers INVALID_ARGUMENT when they are broken.
    """

    def fail(why: str) -> PermioValidationError:
        return PermioValidationError(f"permio: invalid resource URI {uri!r}: {why}")

    if not isinstance(uri, str) or uri == "":
        raise fail("it is empty")
    if not uri.startswith("/"):
        raise fail('it must start with "/" (use resource() to build URIs)')
    if len(uri.encode("utf-8", "surrogatepass")) > MAX_RESOURCE_URI_LENGTH:
        raise fail(f"it is longer than {MAX_RESOURCE_URI_LENGTH} bytes")
    if _BAD_CHARS.search(uri):
        raise fail("it contains whitespace or control characters")
    if "" in uri[1:].split("/"):
        raise fail("it contains an empty segment")


def _assert_slug(slug: object) -> str:
    if not isinstance(slug, str) or not _SLUG.fullmatch(slug):
        raise PermioValidationError(
            f"permio: invalid group name {slug!r}: use 1-64 lower-case letters, digits and hyphens"
        )
    return slug


def group(slug: str) -> str:
    """The principal ID of a group, ``"group:<slug>"``.

    Grant permissions and roles to it, or check it, like any other principal;
    every member of the group holds what the group is granted::

        group("editors")  # "group:editors"
    """
    return GROUP_PRINCIPAL_PREFIX + _assert_slug(slug)


def slug_of(name_or_principal: object) -> str:
    """Accepts a group slug or a ``"group:<slug>"`` principal ID and returns the slug."""
    name = name_or_principal
    if isinstance(name, str) and name.startswith(GROUP_PRINCIPAL_PREFIX):
        name = name[len(GROUP_PRINCIPAL_PREFIX) :]
    return _assert_slug(name)
