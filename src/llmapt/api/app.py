"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from llmapt.api.middleware import request_context_middleware
from llmapt.api.routes import (
    auth,
    closed_loop,
    dashboard,
    evaluations,
    experiments,
    health,
    meta,
    mutations,
    oracles,
    problems,
    providers,
    reports,
    workspace,
)
from llmapt.application.oracle_registry import OracleRegistry
from llmapt.application.ports import (
    CandidateRepository,
    CandidateReviewRepository,
    ClosedLoopRepository,
    ExperimentRepository,
    ExperimentScheduler,
    OracleValidationRepository,
    Sandbox,
    WorkspaceRepository,
)
from llmapt.application.provider_registry import ProviderRegistry
from llmapt.application.readiness import ReadinessProbe
from llmapt.config import Environment, Settings, get_settings
from llmapt.infrastructure.celery_scheduler import build_scheduler
from llmapt.infrastructure.database import create_engine, create_session_factory
from llmapt.infrastructure.memory import (
    InMemoryCandidateRepository,
    InMemoryCandidateReviewRepository,
    InMemoryClosedLoopRepository,
    InMemoryExperimentRepository,
    InMemoryExperimentScheduler,
    InMemoryOracleValidationRepository,
    InMemoryWorkspaceRepository,
)
from llmapt.infrastructure.oracles import build_oracle_registry
from llmapt.infrastructure.persistence.candidates import (
    PostgresCandidateRepository,
    PostgresOracleValidationRepository,
)
from llmapt.infrastructure.persistence.closed_loop import (
    PostgresCandidateReviewRepository,
    PostgresClosedLoopRepository,
)
from llmapt.infrastructure.persistence.experiments import PostgresExperimentRepository
from llmapt.infrastructure.persistence.workspace import PostgresWorkspaceRepository
from llmapt.infrastructure.providers.factory import build_provider_registry
from llmapt.infrastructure.readiness import InfrastructureReadinessProbe
from llmapt.infrastructure.runner import HttpSandbox
from llmapt.logging import configure_logging


def create_app(
    settings: Settings | None = None,
    readiness_probe: ReadinessProbe | None = None,
    provider_registry: ProviderRegistry | None = None,
    experiment_repository: ExperimentRepository | None = None,
    experiment_scheduler: ExperimentScheduler | None = None,
    candidate_repository: CandidateRepository | None = None,
    oracle_validation_repository: OracleValidationRepository | None = None,
    oracle_registry: OracleRegistry | None = None,
    candidate_review_repository: CandidateReviewRepository | None = None,
    closed_loop_repository: ClosedLoopRepository | None = None,
    sandbox: Sandbox | None = None,
    workspace_repository: WorkspaceRepository | None = None,
) -> FastAPI:
    """Build an application without opening external connections on import."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    persistence_engine = None
    sessions = None
    if resolved_settings.environment is not Environment.TEST and (
        experiment_repository is None
        or candidate_repository is None
        or oracle_validation_repository is None
        or candidate_review_repository is None
        or closed_loop_repository is None
        or workspace_repository is None
    ):
        persistence_engine = create_engine(resolved_settings)
        sessions = create_session_factory(persistence_engine)

    if experiment_repository is not None:
        resolved_experiments = experiment_repository
    elif resolved_settings.environment is Environment.TEST:
        resolved_experiments = InMemoryExperimentRepository()
    else:
        assert sessions is not None
        resolved_experiments = PostgresExperimentRepository(sessions)

    if candidate_repository is not None:
        resolved_candidates = candidate_repository
    elif resolved_settings.environment is Environment.TEST:
        resolved_candidates = InMemoryCandidateRepository()
    else:
        assert sessions is not None
        resolved_candidates = PostgresCandidateRepository(sessions)

    if oracle_validation_repository is not None:
        resolved_validations = oracle_validation_repository
    elif resolved_settings.environment is Environment.TEST:
        resolved_validations = InMemoryOracleValidationRepository()
    else:
        assert sessions is not None
        resolved_validations = PostgresOracleValidationRepository(sessions)

    if candidate_review_repository is not None:
        resolved_reviews = candidate_review_repository
    elif resolved_settings.environment is Environment.TEST:
        resolved_reviews = InMemoryCandidateReviewRepository()
    else:
        assert sessions is not None
        resolved_reviews = PostgresCandidateReviewRepository(sessions)

    if closed_loop_repository is not None:
        resolved_closed_loop = closed_loop_repository
    elif resolved_settings.environment is Environment.TEST:
        resolved_closed_loop = InMemoryClosedLoopRepository()
    else:
        assert sessions is not None
        resolved_closed_loop = PostgresClosedLoopRepository(sessions)

    if workspace_repository is not None:
        resolved_workspace = workspace_repository
    elif resolved_settings.environment is Environment.TEST:
        resolved_workspace = InMemoryWorkspaceRepository()
    else:
        assert sessions is not None
        resolved_workspace = PostgresWorkspaceRepository(sessions)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger = structlog.get_logger()
        logger.info(
            "application_started",
            environment=resolved_settings.environment.value,
            version=resolved_settings.app_version,
        )
        yield
        if persistence_engine is not None:
            await persistence_engine.dispose()
        logger.info("application_stopped")

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Programming capability boundary evaluation control plane.",
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.login_failures = {}
    app.state.readiness_probe = readiness_probe or InfrastructureReadinessProbe(resolved_settings)
    app.state.provider_registry = provider_registry or build_provider_registry(resolved_settings)
    app.state.experiment_repository = resolved_experiments
    app.state.candidate_repository = resolved_candidates
    app.state.oracle_validation_repository = resolved_validations
    app.state.candidate_review_repository = resolved_reviews
    app.state.closed_loop_repository = resolved_closed_loop
    app.state.workspace_repository = resolved_workspace
    app.state.oracle_registry = oracle_registry or build_oracle_registry()
    app.state.sandbox = sandbox or HttpSandbox(
        resolved_settings.runner_url,
        resolved_settings.runner_token.get_secret_value(),
        resolved_settings.runner_timeout_seconds,
    )
    app.state.experiment_storage_ephemeral = isinstance(
        resolved_experiments,
        InMemoryExperimentRepository,
    )
    app.state.experiment_scheduler = experiment_scheduler or (
        InMemoryExperimentScheduler()
        if resolved_settings.environment is Environment.TEST
        else build_scheduler(resolved_settings)
    )
    app.middleware("http")(request_context_middleware)
    app.include_router(health.router)
    app.include_router(meta.router)
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(workspace.router)
    app.include_router(reports.router)
    app.include_router(evaluations.router)
    app.include_router(closed_loop.router)
    app.include_router(experiments.router)
    app.include_router(mutations.router)
    app.include_router(oracles.router)
    app.include_router(providers.router)
    app.include_router(problems.router)
    return app
