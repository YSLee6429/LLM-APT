"""Local administrator authentication and temporary guest sessions."""

import secrets
import time
from dataclasses import replace
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status

from llmapt.api.auth import require_user
from llmapt.api.m3_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
)
from llmapt.application.auth import hash_password, issue_token, verify_password
from llmapt.application.ports import WorkspaceRepository
from llmapt.config import Settings
from llmapt.domain.errors import EvaluationError
from llmapt.domain.workspace import WorkspaceRole, WorkspaceUser

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _response(user: WorkspaceUser) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


async def _ensure_bootstrap(request: Request) -> None:
    settings = cast(Settings, request.app.state.settings)
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    username = settings.bootstrap_admin_username.casefold().strip()
    if await repository.get_user_by_username(username) is None:
        await repository.save_user(
            WorkspaceUser(
                username=username,
                display_name=settings.bootstrap_admin_display_name,
                role=WorkspaceRole.ADMIN,
                password_hash=hash_password(settings.bootstrap_admin_password.get_secret_value()),
            )
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest) -> LoginResponse:
    username = body.username.casefold().strip()
    client_host = request.client.host if request.client is not None else "unknown"
    attempt_key = f"{client_host}:{username}"
    failures = cast(dict[str, tuple[int, float]], request.app.state.login_failures)
    failure_count, blocked_until = failures.get(attempt_key, (0, 0.0))
    now = time.monotonic()
    if blocked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many login attempts; retry later",
            headers={"Retry-After": str(max(1, int(blocked_until - now)))},
        )
    await _ensure_bootstrap(request)
    settings = cast(Settings, request.app.state.settings)
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    user = await repository.get_user_by_username(username)
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        failure_count += 1
        failures[attempt_key] = (
            failure_count,
            now + 60.0 if failure_count >= 5 else 0.0,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    failures.pop(attempt_key, None)
    return LoginResponse(
        access_token=issue_token(
            user, settings.auth_secret.get_secret_value(), settings.access_token_ttl_minutes
        ),
        expires_in_seconds=settings.access_token_ttl_minutes * 60,
        user=_response(user),
    )


@router.post("/guest", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_session(request: Request) -> LoginResponse:
    """Create a short-lived, non-reusable local guest identity."""

    settings = cast(Settings, request.app.state.settings)
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    for _attempt in range(3):
        suffix = secrets.token_hex(4)
        user = WorkspaceUser(
            username=f"guest-{suffix}",
            display_name=f"Guest {suffix[:4].upper()}",
            role=WorkspaceRole.GUEST,
            password_hash=hash_password(secrets.token_urlsafe(24)),
        )
        try:
            await repository.save_user(user)
            break
        except EvaluationError:
            if _attempt == 2:
                raise
    return LoginResponse(
        access_token=issue_token(
            user, settings.auth_secret.get_secret_value(), settings.guest_token_ttl_minutes
        ),
        expires_in_seconds=settings.guest_token_ttl_minutes * 60,
        user=_response(user),
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    user: Annotated[WorkspaceUser, Depends(require_user)],
) -> None:
    if user.role is WorkspaceRole.GUEST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="guest sessions do not have reusable passwords",
        )
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current password is incorrect",
        )
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    await repository.update_user(replace(user, password_hash=hash_password(body.new_password)))


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[WorkspaceUser, Depends(require_user)]) -> UserResponse:
    return _response(user)
