from __future__ import annotations

import hashlib
import hmac
import os
from base64 import b64decode, b64encode

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password vazio")

    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )

    return "$".join(
        [
            _ALGORITHM,
            str(_ITERATIONS),
            b64encode(salt).decode("ascii"),
            b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False

    if hashed.startswith(f"{_ALGORITHM}$"):
        return _verify_pbkdf2(password, hashed)

    return _verify_legacy_sha256(password, hashed)


def is_legacy_hash(hashed: str) -> bool:
    return bool(hashed) and not hashed.startswith(f"{_ALGORITHM}$")


def _verify_pbkdf2(password: str, hashed: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = hashed.split("$", 3)

        if algorithm != _ALGORITHM:
            return False

        iterations = int(iterations_text)
        salt = b64decode(salt_text.encode("ascii"))
        expected = b64decode(digest_text.encode("ascii"))

        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(calculated, expected)

    except Exception:
        return False


def _verify_legacy_sha256(password: str, hashed: str) -> bool:
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, hashed)
