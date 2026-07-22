"""Authentication dependencies shared by M3 API routes."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from llmapt.application.auth import parse_token
from llmapt.application.ports import WorkspaceRepository
from llmapt.config import Settings
from llmapt.domain.workspace import WorkspaceRole, WorkspaceUser

bearer = HTTPBearer(auto_error=False)


async def optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> WorkspaceUser | None:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        return None
    settings = cast(Settings, request.app.state.settings)
    claims = parse_token(credentials.credentials, settings.auth_secret.get_secret_value())
    if claims is None:
        return None
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    user = await repository.get_user(claims.user_id)
    if (
        user is None
        or not user.active
        or user.username != claims.username
        or user.role is not claims.role
    ):
        return None
    return user


async def require_user(
    user: Annotated[WorkspaceUser | None, Depends(optional_user)],
) -> WorkspaceUser:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="valid bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(
    *roles: WorkspaceRole,
) -> Callable[..., Coroutine[Any, Any, WorkspaceUser]]:
    async def dependency(
        user: Annotated[WorkspaceUser, Depends(require_user)],
    ) -> WorkspaceUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return dependency
