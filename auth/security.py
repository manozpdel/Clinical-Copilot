"""Password hashing utilities.

This module is responsible ONLY for hashing and verifying passwords.
It contains no JWT, OAuth, or dependency-injection logic.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_BCRYPT_MAX_BYTES = 72


def _truncate_to_bcrypt_limit(password: str) -> str:
    """Truncate a password to bcrypt's 72-byte input limit.

    bcrypt silently ignores any bytes beyond the 72nd, so truncating
    here (rather than relying on the underlying library to do it) keeps
    hashing and verification behavior explicit and version-independent.

    Args:
        password: The plaintext password to truncate.

    Returns:
        str: The password, truncated to at most 72 UTF-8 encoded bytes.
    """
    encoded = password.encode("utf-8")
    if len(encoded) <= _BCRYPT_MAX_BYTES:
        return password
    return encoded[:_BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    """Hash a plaintext password.

    Args:
        password: The plaintext password to hash.

    Returns:
        str: The bcrypt password hash.
    """
    return _pwd_context.hash(_truncate_to_bcrypt_limit(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Args:
        plain_password: The plaintext password supplied by the user.
        hashed_password: The stored bcrypt password hash.

    Returns:
        bool: True if the password matches the hash.
    """
    return _pwd_context.verify(_truncate_to_bcrypt_limit(plain_password), hashed_password)
