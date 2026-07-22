"""Password hashing and signed local access tokens for the M3 research workspace."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from llmapt.domain.workspace import WorkspaceRole, WorkspaceUser

_ITERATIONS = 240_000


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < 10:
        raise ValueError("password must contain at least 10 characters")
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), actual_salt, _ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        _ITERATIONS,
        base64.urlsafe_b64encode(actual_salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_text, expected_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text + "==")
        expected = base64.urlsafe_b64decode(expected_text + "==")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: UUID
    username: str
    role: WorkspaceRole
    expires_at: datetime


def issue_token(user: WorkspaceUser, secret: str, ttl_minutes: int) -> str:
    payload = {
        "sub": str(user.user_id),
        "username": user.username,
        "role": user.role.value,
        "exp": int((datetime.now(UTC) + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    body = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        .decode()
        .rstrip("=")
    )
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"


def parse_token(token: str, secret: str) -> TokenClaims | None:
    try:
        body, signature_text = token.split(".", 1)
        expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
        signature = base64.urlsafe_b64decode(signature_text + "==")
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=="))
        expires_at = datetime.fromtimestamp(int(payload["exp"]), UTC)
        if expires_at <= datetime.now(UTC):
            return None
        return TokenClaims(
            user_id=UUID(payload["sub"]),
            username=str(payload["username"]),
            role=WorkspaceRole(payload["role"]),
            expires_at=expires_at,
        )
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
