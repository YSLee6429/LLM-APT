"""Live dependency checks for API readiness."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping

import httpx
from celery import Celery
from redis.asyncio import Redis

from llmapt.config import Settings
from llmapt.infrastructure.database import create_engine, ping_database


class InfrastructureReadinessProbe:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def check(self) -> Mapping[str, str]:
        checks: dict[str, Callable[[], Awaitable[bool]]] = {
            "database": self._database,
            "broker": self._broker,
            "redis": self._redis,
            "object_store": self._object_store,
            "runner": self._runner,
        }
        results = await asyncio.gather(*(check() for check in checks.values()))
        return {
            "configuration": "ready",
            **{
                component: "ready" if available else "unavailable"
                for component, available in zip(checks, results, strict=True)
            },
        }

    async def _database(self) -> bool:
        engine = create_engine(self._settings)
        try:
            await asyncio.wait_for(ping_database(engine), timeout=3)
            return True
        except Exception:
            return False
        finally:
            await engine.dispose()

    async def _redis(self) -> bool:
        client = Redis.from_url(self._settings.redis_url, socket_connect_timeout=3)
        try:
            return bool(await asyncio.wait_for(client.ping(), timeout=3))
        except Exception:
            return False
        finally:
            await client.aclose()

    async def _object_store(self) -> bool:
        endpoint = self._settings.object_store_endpoint.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                response = await client.get(f"{endpoint}/minio/health/ready")
            return response.status_code == 200
        except Exception:
            return False

    async def _broker(self) -> bool:
        return await asyncio.to_thread(self._check_broker_sync)

    def _check_broker_sync(self) -> bool:
        app = Celery("llmapt-readiness", broker=self._settings.broker_url)
        connection = app.connection_for_read()
        try:
            connection.ensure_connection(max_retries=1, timeout=3)
            return True
        except Exception:
            return False
        finally:
            connection.close()

    async def _runner(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                response = await client.get(f"{self._settings.runner_url.rstrip('/')}/health")
            return response.status_code == 200
        except Exception:
            return False
