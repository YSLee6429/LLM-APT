"""Deterministic M1 composition root with no source execution."""

from __future__ import annotations

from enum import StrEnum

from llmapt.application.evaluation import EvaluationRequest, EvaluationService
from llmapt.application.ports import CompilationResult, ExecutionResult
from llmapt.domain.problems import ProblemSpec, ResourceLimits, TestCase
from llmapt.domain.results import EvaluationReport
from llmapt.infrastructure.memory import (
    DeterministicModelProvider,
    InMemoryArtifactStore,
    InMemoryRunRepository,
    ScriptedSandbox,
)


class MockScenario(StrEnum):
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    COMPILE_ERROR = "compile_error"


def demo_problem() -> ProblemSpec:
    return ProblemSpec(
        problem_id="m1-double",
        title="Double an Integer",
        statement="Read one integer and print twice its value.",
        language="cpp",
        tests=(
            TestCase("positive", b"2\n", b"4\n", hidden=False),
            TestCase("negative", b"-3\n", b"-6\n"),
        ),
        limits=ResourceLimits(time_limit_ms=1000, memory_limit_mb=128),
    )


async def run_mock_scenario(scenario: MockScenario, random_seed: int = 7) -> EvaluationReport:
    """Run a complete evaluation from scripted facts and return its evidence report."""

    compilation = None
    negative_output = b"-6\n"
    if scenario is MockScenario.WRONG_ANSWER:
        negative_output = b"6\n"
    elif scenario is MockScenario.COMPILE_ERROR:
        compilation = CompilationResult(
            succeeded=False,
            artifact_token=None,
            diagnostics=b"mock compiler: expected ';'",
            duration_ms=4,
        )

    sandbox = ScriptedSandbox(
        executions={
            b"2\n": ExecutionResult(0, b"4\n", b"", 2),
            b"-3\n": ExecutionResult(0, negative_output, b"", 2),
        },
        compilation=compilation,
    )
    service = EvaluationService(
        provider=DeterministicModelProvider(
            source="#include <iostream>\nint main() { return 0; }\n"
        ),
        sandbox=sandbox,
        runs=InMemoryRunRepository(),
        artifacts=InMemoryArtifactStore(),
    )
    return await service.evaluate(
        EvaluationRequest(
            problem=demo_problem(),
            prompt="Return a C++ solution without Markdown fences.",
            random_seed=random_seed,
            prompt_template_version="m1-demo-v1",
            model_parameters={"temperature": 0, "max_tokens": 1024},
        )
    )
