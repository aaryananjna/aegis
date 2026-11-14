"""Password hashing and opaque tokens.

Passwords: argon2id (argon2-cffi defaults). Login and device tokens: 32 random bytes, sent to
the client once; the database keeps only their sha256, so a database leak can't log anyone in.
"""
from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_ph = PasswordHasher()
# Hashed once so a login for an unknown email takes as long as one with a wrong password.
_DUMMY_HASH = _ph.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    try:
        return _ph.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()
