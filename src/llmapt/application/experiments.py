"""Experiment planning application service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from llmapt.application.ports import ExperimentRepository
from llmapt.application.provider_registry import ProviderRegistry
from llmapt.domain.experiments import ExperimentManifest, ParameterValue
from llmapt.domain.problems import ProblemSpec


@dataclass(frozen=True, slots=True)
class PlanExperimentRequest:
    problem: ProblemSpec
    provider_key: str
    prompt_template_version: str
    random_seed: int
    repetitions: int
    parameters: Mapping[str, ParameterValue]


class ExperimentPlanner:
    def __init__(self, providers: ProviderRegistry, experiments: ExperimentRepository) -> None:
        self._providers = providers
        self._experiments = experiments

    async def plan(self, request: PlanExperimentRequest) -> ExperimentManifest:
        identity = await self._providers.get(request.provider_key).identify()
        manifest = ExperimentManifest(
            problem_id=request.problem.problem_id,
            statement_digest=request.problem.statement_digest,
            test_suite_digest=request.problem.test_suite_digest,
            target=identity,
            prompt_template_version=request.prompt_template_version,
            random_seed=request.random_seed,
            repetitions=request.repetitions,
            parameters=tuple(sorted(request.parameters.items())),
        )
        await self._experiments.save(manifest)
        return manifest
