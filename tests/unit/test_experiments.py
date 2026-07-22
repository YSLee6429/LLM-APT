from dataclasses import replace

import pytest

from llmapt.application.experiments import ExperimentPlanner, PlanExperimentRequest
from llmapt.application.provider_registry import ProviderNotFoundError, ProviderRegistry
from llmapt.domain.entities import ModelIdentity
from llmapt.domain.experiments import ExperimentManifest
from llmapt.domain.problems import ProblemSpec, ResourceLimits
from llmapt.domain.problems import TestCase as ProblemTestCase
from llmapt.infrastructure.memory import DeterministicModelProvider, InMemoryExperimentRepository


def _problem() -> ProblemSpec:
    return ProblemSpec(
        problem_id="double",
        title="Double",
        statement="Print twice the input.",
        language="cpp",
        tests=(ProblemTestCase("one", b"1\n", b"2\n"),),
        limits=ResourceLimits(1000, 128),
    )


def _registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        "local",
        DeterministicModelProvider("source", ModelIdentity("local", "deterministic", "m2")),
        external=False,
    )
    return registry


@pytest.mark.asyncio
async def test_planner_canonicalizes_parameters_and_digest() -> None:
    experiments = InMemoryExperimentRepository()
    planner = ExperimentPlanner(_registry(), experiments)
    request = PlanExperimentRequest(
        problem=_problem(),
        provider_key="LOCAL",
        prompt_template_version="v1",
        random_seed=9,
        repetitions=3,
        parameters={"temperature": 0, "max_tokens": 2048},
    )

    first = await planner.plan(request)
    second = await planner.plan(request)

    assert first.parameters == (("max_tokens", 2048), ("temperature", 0))
    assert first.plan_digest == second.plan_digest
    assert first.experiment_id != second.experiment_id
    assert first.target.model == "deterministic"
    assert await experiments.get(first.experiment_id) == first


@pytest.mark.asyncio
async def test_unknown_provider_is_rejected() -> None:
    planner = ExperimentPlanner(_registry(), InMemoryExperimentRepository())
    request = PlanExperimentRequest(_problem(), "missing", "v1", 7, 1, {})

    with pytest.raises(ProviderNotFoundError):
        await planner.plan(request)


def test_manifest_validates_repetitions_and_canonical_parameters() -> None:
    manifest = ExperimentManifest(
        "problem", "statement", "suite", ModelIdentity("p", "m"), "v1", 7, 1
    )

    with pytest.raises(ValueError, match="between 1 and 100"):
        replace(manifest, repetitions=0)
    with pytest.raises(ValueError, match="unique and sorted"):
        replace(manifest, parameters=(("z", 1), ("a", 2)))
