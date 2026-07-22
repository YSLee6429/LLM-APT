import json
from dataclasses import replace
from uuid import UUID

import pytest

from llmapt.application.evaluation import EvaluationRequest, EvaluationService
from llmapt.application.ports import CompilationResult, ExecutionResult, ModelRequest, ModelResponse
from llmapt.domain.entities import ModelIdentity
from llmapt.domain.enums import EvidenceLevel, Verdict
from llmapt.domain.errors import EvaluationError
from llmapt.domain.problems import ProblemSpec, ResourceLimits
from llmapt.domain.problems import TestCase as ProblemTestCase
from llmapt.infrastructure.memory import (
    DeterministicModelProvider,
    InMemoryArtifactStore,
    InMemoryRunRepository,
    ScriptedSandbox,
)


def _problem() -> ProblemSpec:
    return ProblemSpec(
        problem_id="double",
        title="Double",
        statement="Read an integer and print twice its value.",
        language="cpp",
        tests=(
            ProblemTestCase("sample", b"2\n", b"4\n", hidden=False),
            ProblemTestCase("negative", b"-3\n", b"-6\n"),
        ),
        limits=ResourceLimits(time_limit_ms=1000, memory_limit_mb=128),
    )


def _execution(stdout: bytes) -> ExecutionResult:
    return ExecutionResult(exit_code=0, stdout=stdout, stderr=b"", duration_ms=3)


def _request() -> EvaluationRequest:
    return EvaluationRequest(
        problem=_problem(),
        prompt="Solve the problem and return C++ source only.",
        random_seed=7,
        prompt_template_version="m1-test-v1",
        model_parameters={"temperature": 0, "max_tokens": 1024},
    )


@pytest.mark.asyncio
async def test_accepted_evaluation_persists_manifest_and_artifacts() -> None:
    provider = DeterministicModelProvider(source="int main() { return 0; }")
    sandbox = ScriptedSandbox({b"2\n": _execution(b"4\n"), b"-3\n": _execution(b"-6\n")})
    runs = InMemoryRunRepository()
    artifacts = InMemoryArtifactStore()
    service = EvaluationService(provider, sandbox, runs, artifacts)

    report = await service.evaluate(_request())

    assert report.verdict is Verdict.ACCEPTED
    assert report.evidence_level is EvidenceLevel.NONE
    assert report.passed_cases == report.total_cases == 2
    assert len(sandbox.compile_calls) == 1
    assert sandbox.execute_calls == [b"2\n", b"-3\n"]
    assert await runs.get(report.run_id) is not None
    assert report.report_artifact_uri is not None
    assert report.compile_diagnostics_artifact_uri.startswith("memory://")
    assert report.cases[0].actual_output_artifact_uri.startswith("memory://")
    report_key = report.report_artifact_uri.removeprefix("memory://")
    persisted = json.loads((await artifacts.get(report_key)).decode())
    assert persisted["problem_id"] == "double"
    assert persisted["verdict"] == "accepted"


@pytest.mark.asyncio
async def test_evaluation_compiles_extracted_fenced_source() -> None:
    provider = DeterministicModelProvider(
        source="Explanation first.\n```cpp\nint main() { return 0; }\n```"
    )
    sandbox = ScriptedSandbox({b"2\n": _execution(b"4\n"), b"-3\n": _execution(b"-6\n")})
    artifacts = InMemoryArtifactStore()
    service = EvaluationService(provider, sandbox, InMemoryRunRepository(), artifacts)

    report = await service.evaluate(_request())

    assert report.verdict is Verdict.ACCEPTED
    assert sandbox.compile_calls[0][0] == b"int main() { return 0; }"
    source_key = report.source_artifact_uri.removeprefix("memory://")
    assert await artifacts.get(source_key) == b"int main() { return 0; }"


@pytest.mark.asyncio
async def test_configuration_digest_is_stable_and_prompt_sensitive() -> None:
    async def evaluate(request: EvaluationRequest) -> tuple[str, InMemoryRunRepository]:
        runs = InMemoryRunRepository()
        service = EvaluationService(
            DeterministicModelProvider(source="source"),
            ScriptedSandbox({b"2\n": _execution(b"4\n"), b"-3\n": _execution(b"-6\n")}),
            runs,
            InMemoryArtifactStore(),
        )
        report = await service.evaluate(request)
        return str(report.run_id), runs

    original = _request()
    first_id, first_runs = await evaluate(original)
    second_id, second_runs = await evaluate(original)
    changed_id, changed_runs = await evaluate(replace(original, prompt="A changed prompt"))

    first = await first_runs.get(UUID(first_id))
    second = await second_runs.get(UUID(second_id))
    changed = await changed_runs.get(UUID(changed_id))
    assert first is not None and second is not None and changed is not None
    assert first.configuration_digest == second.configuration_digest
    assert first.configuration_digest != changed.configuration_digest


@pytest.mark.asyncio
async def test_wrong_answer_records_case_level_digests() -> None:
    provider = DeterministicModelProvider(source="wrong source")
    sandbox = ScriptedSandbox({b"2\n": _execution(b"4\n"), b"-3\n": _execution(b"6\n")})
    service = EvaluationService(provider, sandbox, InMemoryRunRepository(), InMemoryArtifactStore())

    report = await service.evaluate(_request())

    assert report.verdict is Verdict.WRONG_ANSWER
    assert report.evidence_level is EvidenceLevel.OBSERVED_DIFFERENCE
    assert report.cases[0].verdict is Verdict.ACCEPTED
    assert report.cases[1].verdict is Verdict.WRONG_ANSWER
    assert report.cases[1].expected_output_digest != report.cases[1].actual_output_digest


@pytest.mark.asyncio
async def test_compile_error_does_not_execute_test_cases() -> None:
    compilation = CompilationResult(
        succeeded=False,
        artifact_token=None,
        diagnostics=b"syntax error",
        duration_ms=5,
    )
    sandbox = ScriptedSandbox({}, compilation=compilation)
    service = EvaluationService(
        DeterministicModelProvider(source="not C++"),
        sandbox,
        InMemoryRunRepository(),
        InMemoryArtifactStore(),
    )

    report = await service.evaluate(_request())

    assert report.verdict is Verdict.COMPILE_ERROR
    assert report.cases == ()
    assert sandbox.execute_calls == []


class ChangingIdentityProvider:
    async def identify(self) -> ModelIdentity:
        return ModelIdentity("mock", "before")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        del request
        return ModelResponse(ModelIdentity("mock", "after"), "source")


@pytest.mark.asyncio
async def test_model_identity_must_remain_stable() -> None:
    service = EvaluationService(
        ChangingIdentityProvider(),
        ScriptedSandbox({}),
        InMemoryRunRepository(),
        InMemoryArtifactStore(),
    )

    with pytest.raises(EvaluationError, match="identity changed"):
        await service.evaluate(_request())
