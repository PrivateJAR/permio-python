"""Local API key format checks (no network)."""

from __future__ import annotations

import re
import zlib

from ._errors import PermioConfigError

# Mirrors go-common/middleware/apikey: "perms_" + 32 random base62 characters +
# 6 base62 characters encoding the CRC32 (IEEE) of those 32, 44 characters total.
_PREFIX = "perms_"
_RANDOM_LENGTH = 32
_CHECKSUM_LENGTH = 6
API_KEY_LENGTH = len(_PREFIX) + _RANDOM_LENGTH + _CHECKSUM_LENGTH
_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_ALPHABET_SET = frozenset(_ALPHABET)

_JWT = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


def _checksum(body: str) -> str:
    value = zlib.crc32(body.encode("ascii")) & 0xFFFFFFFF
    out = []
    for _ in range(_CHECKSUM_LENGTH):
        value, rem = divmod(value, 62)
        out.append(_ALPHABET[rem])
    return "".join(reversed(out))


def validate_api_key(key: object) -> str:
    """Checks that ``key`` looks like a perms.io API key and returns its kind.

    Returns ``"opaque"`` for ``perms_...`` keys (checked for length, alphabet and
    CRC32 checksum, so a typo is caught before any request is made) and
    ``"jwt"`` for legacy JWT keys (only checked for the three-part shape). This
    does not tell you whether the key exists or is still valid; only the API can.

    Raises:
        PermioConfigError: if the key is missing or malformed.
    """
    if not isinstance(key, str) or key == "":
        raise PermioConfigError("permio: api_key is required (or set PERMIO_API_KEY)")
    if key.startswith(_PREFIX):
        if len(key) != API_KEY_LENGTH:
            raise PermioConfigError(
                f"permio: malformed API key (expected {API_KEY_LENGTH} characters starting with "
                f'"{_PREFIX}", got {len(key)})'
            )
        rest = key[len(_PREFIX) :]
        if any(c not in _ALPHABET_SET for c in rest):
            raise PermioConfigError(
                "permio: malformed API key (characters after perms_ must be 0-9, A-Z or a-z)"
            )
        if _checksum(rest[:_RANDOM_LENGTH]) != rest[_RANDOM_LENGTH:]:
            raise PermioConfigError(
                "permio: API key checksum mismatch; check it was copied correctly"
            )
        return "opaque"
    if _JWT.match(key):
        return "jwt"
    raise PermioConfigError(
        'permio: malformed API key (expected a "perms_" key from the dashboard, or a legacy JWT key)'
    )


def is_valid_api_key(key: object) -> bool:
    """Returns True if ``key`` passes :func:`validate_api_key`."""
    try:
        validate_api_key(key)
    except PermioConfigError:
        return False
    return True
