"""Cross-cutting HTTP request context."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import Request, Response
from structlog.contextvars import bind_contextvars, clear_contextvars


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach a request ID and emit one completion event per request."""

    settings = request.app.state.settings
    request_id = request.headers.get(settings.request_id_header) or uuid4().hex
    clear_contextvars()
    bind_contextvars(request_id=request_id)
    started = perf_counter()
    logger = structlog.get_logger()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
        )
        raise
    finally:
        duration_ms = round((perf_counter() - started) * 1000, 3)

    response.headers[settings.request_id_header] = request_id
    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    clear_contextvars()
    return response
