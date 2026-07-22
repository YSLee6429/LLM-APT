"""Command-line entry point for local operation and diagnostics."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import asdict

import uvicorn

from llmapt import __version__
from llmapt.config import get_settings
from llmapt.demo import MockScenario, run_mock_scenario
from llmapt.infrastructure.providers.factory import build_provider_registry


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llmapt", description="LLM-APT control utility")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("version", help="print the installed package version")
    subparsers.add_parser("doctor", help="validate and print non-secret configuration")
    subparsers.add_parser("providers", help="list configured model providers")

    mock = subparsers.add_parser("mock-evaluate", help="run a deterministic M1 evaluation")
    mock.add_argument(
        "--scenario",
        choices=[scenario.value for scenario in MockScenario],
        default=MockScenario.ACCEPTED.value,
    )

    serve = subparsers.add_parser("serve", help="run the development API server")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--reload", action="store_true")
    return parser


def _doctor() -> int:
    settings = get_settings()
    report = {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment.value,
        "log_format": settings.log_format.value,
        "database_driver": settings.database_url.split(":", maxsplit=1)[0],
        "broker_driver": settings.broker_url.split(":", maxsplit=1)[0],
        "redis_configured": bool(settings.redis_url),
        "object_store_configured": bool(settings.object_store_endpoint),
        "external_model_calls_enabled": settings.external_model_calls_enabled,
        "external_model_configured": bool(
            settings.model_name and settings.model_api_endpoint and settings.model_api_key
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


async def _providers() -> int:
    descriptors = await build_provider_registry(get_settings()).describe()
    report = [
        {
            "key": descriptor.key,
            "provider": descriptor.identity.provider,
            "model": descriptor.identity.model,
            "revision": descriptor.identity.revision,
            "external": descriptor.external,
        }
        for descriptor in descriptors
    ]
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "doctor":
        return _doctor()
    if args.command == "providers":
        return asyncio.run(_providers())
    if args.command == "mock-evaluate":
        report = asyncio.run(run_mock_scenario(MockScenario(args.scenario)))
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=str))
        return 0
    if args.command == "serve":
        settings = get_settings()
        uvicorn.run(
            "llmapt.main:app",
            host=args.host or settings.api_host,
            port=args.port or settings.api_port,
            reload=args.reload,
        )
        return 0
    raise AssertionError("unreachable command")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
