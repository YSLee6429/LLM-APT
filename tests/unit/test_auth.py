from datetime import UTC, datetime

from llmapt.application.auth import hash_password, issue_token, parse_token, verify_password
from llmapt.domain.workspace import WorkspaceRole, WorkspaceUser


def test_password_hash_round_trip_and_rejection() -> None:
    encoded = hash_password("correct-horse-battery-staple")

    assert verify_password("correct-horse-battery-staple", encoded)
    assert not verify_password("incorrect-password", encoded)
    assert not verify_password("anything", "invalid")
    assert "correct-horse" not in encoded


def test_signed_token_round_trip_and_tamper_rejection() -> None:
    user = WorkspaceUser(
        username="researcher",
        display_name="Researcher",
        role=WorkspaceRole.RESEARCHER,
        password_hash="not-used",
    )
    token = issue_token(user, "test-secret", 30)

    claims = parse_token(token, "test-secret")
    assert claims is not None
    assert claims.user_id == user.user_id
    assert claims.role is WorkspaceRole.RESEARCHER
    assert claims.expires_at > datetime.now(UTC)
    assert parse_token(token + "x", "test-secret") is None
    assert parse_token(token, "different-secret") is None
