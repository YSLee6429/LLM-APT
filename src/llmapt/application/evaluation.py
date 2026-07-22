"""Reproducible evaluation orchestration independent of concrete adapters."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace

from llmapt.application.judge import classify_execution
from llmapt.application.ports import (
    ArtifactStore,
    ModelProvider,
    ModelRequest,
    RunRepository,
    Sandbox,
)
from llmapt.application.source_extraction import extract_candidate_source
from llmapt.domain.digests import digest_bytes, digest_mapping, digest_text
from llmapt.domain.entities import RunManifest
from llmapt.domain.enums import EvidenceLevel, Verdict
from llmapt.domain.errors import EvaluationError
from llmapt.domain.problems import ProblemSpec
from llmapt.domain.results import CaseEvaluation, EvaluationReport


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    problem: ProblemSpec
    prompt: str
    random_seed: int
    prompt_template_version: str
    model_parameters: Mapping[str, str | int | float | bool]


class EvaluationService:
    """Coordinate model generation, compilation, execution, judging and evidence storage."""

    def __init__(
        self,
        provider: ModelProvider,
        sandbox: Sandbox,
        runs: RunRepository,
        artifacts: ArtifactStore,
    ) -> None:
        self._provider = provider
        self._sandbox = sandbox
        self._runs = runs
        self._artifacts = artifacts

    async def evaluate(self, request: EvaluationRequest) -> EvaluationReport:
        identity = await self._provider.identify()
        manifest = RunManifest(
            target=identity,
            random_seed=request.random_seed,
            prompt_template_version=request.prompt_template_version,
            configuration_digest=self._configuration_digest(request),
        )
        await self._runs.save(manifest)

        response = await self._provider.generate(
            ModelRequest(
                prompt=request.prompt,
                language=request.problem.language,
                parameters=request.model_parameters,
            )
        )
        if response.identity != identity:
            raise EvaluationError("model identity changed during evaluation")

        raw_response = response.raw_text.encode("utf-8")
        extracted = extract_candidate_source(response.raw_text, request.problem.language)
        candidate_source = extracted.source.encode("utf-8")
        prefix = f"runs/{manifest.run_id}"
        response_uri = await self._artifacts.put(
            f"{prefix}/model-response.txt",
            raw_response,
            {"kind": "model_response", "sha256": digest_bytes(raw_response)},
        )
        source_uri = await self._artifacts.put(
            f"{prefix}/candidate.{request.problem.language}",
            candidate_source,
            {
                "kind": "candidate_source",
                "sha256": digest_bytes(candidate_source),
                "extracted_from_fence": str(extracted.used_fence).lower(),
            },
        )

        compilation = await self._sandbox.compile(
            candidate_source,
            request.problem.language,
            request.problem.limits,
        )
        compile_diagnostics_uri = await self._artifacts.put(
            f"{prefix}/compile-diagnostics.txt",
            compilation.diagnostics,
            {"kind": "compile_diagnostics"},
        )
        if not compilation.succeeded or compilation.artifact_token is None:
            report = EvaluationReport(
                run_id=manifest.run_id,
                problem_id=request.problem.problem_id,
                model_provider=identity.provider,
                model_name=identity.model,
                verdict=Verdict.COMPILE_ERROR,
                evidence_level=EvidenceLevel.OBSERVED_DIFFERENCE,
                cases=(),
                source_artifact_uri=source_uri,
                response_artifact_uri=response_uri,
                compile_diagnostics_artifact_uri=compile_diagnostics_uri,
            )
            return await self._persist_report(prefix, report)

        case_results: list[CaseEvaluation] = []
        for test_case in request.problem.tests:
            execution = await self._sandbox.execute(
                compilation.artifact_token,
                (),
                test_case.standard_input,
                request.problem.limits,
            )
            verdict = classify_execution(
                execution,
                test_case.expected_output,
                request.problem.output_policy,
            )
            actual_output_uri = await self._artifacts.put(
                f"{prefix}/cases/{test_case.case_id}/stdout.bin",
                execution.stdout,
                {"kind": "actual_output", "verdict": verdict.value},
            )
            stderr_uri = await self._artifacts.put(
                f"{prefix}/cases/{test_case.case_id}/stderr.bin",
                execution.stderr,
                {"kind": "standard_error", "verdict": verdict.value},
            )
            case_results.append(
                CaseEvaluation(
                    case_id=test_case.case_id,
                    verdict=verdict,
                    input_digest=test_case.input_digest,
                    expected_output_digest=test_case.expected_output_digest,
                    actual_output_digest=digest_bytes(execution.stdout),
                    duration_ms=execution.duration_ms,
                    exit_code=execution.exit_code,
                    stderr_digest=digest_bytes(execution.stderr),
                    actual_output_artifact_uri=actual_output_uri,
                    stderr_artifact_uri=stderr_uri,
                )
            )

        overall = self._aggregate_verdict(case_results)
        evidence_level = (
            EvidenceLevel.NONE if overall is Verdict.ACCEPTED else EvidenceLevel.OBSERVED_DIFFERENCE
        )
        report = EvaluationReport(
            run_id=manifest.run_id,
            problem_id=request.problem.problem_id,
            model_provider=identity.provider,
            model_name=identity.model,
            verdict=overall,
            evidence_level=evidence_level,
            cases=tuple(case_results),
            source_artifact_uri=source_uri,
            response_artifact_uri=response_uri,
            compile_diagnostics_artifact_uri=compile_diagnostics_uri,
        )
        return await self._persist_report(prefix, report)

    @staticmethod
    def _configuration_digest(request: EvaluationRequest) -> str:
        values: dict[str, str | int | float | bool] = {
            "problem_id": request.problem.problem_id,
            "prompt_digest": digest_text(request.prompt),
            "statement_digest": request.problem.statement_digest,
            "test_suite_digest": request.problem.test_suite_digest,
            "language": request.problem.language,
            "output_policy": request.problem.output_policy.value,
            "time_limit_ms": request.problem.limits.time_limit_ms,
            "memory_limit_mb": request.problem.limits.memory_limit_mb,
            "process_limit": request.problem.limits.process_limit,
            "output_limit_bytes": request.problem.limits.output_limit_bytes,
            "random_seed": request.random_seed,
            "prompt_template_version": request.prompt_template_version,
        }
        values.update({f"model.{key}": value for key, value in request.model_parameters.items()})
        return digest_mapping(values)

    @staticmethod
    def _aggregate_verdict(cases: list[CaseEvaluation]) -> Verdict:
        for case in cases:
            if case.verdict is not Verdict.ACCEPTED:
                return case.verdict
        return Verdict.ACCEPTED

    async def _persist_report(
        self,
        prefix: str,
        report: EvaluationReport,
    ) -> EvaluationReport:
        payload = json.dumps(
            asdict(report),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        uri = await self._artifacts.put(
            f"{prefix}/report.json",
            payload,
            {"kind": "evaluation_report", "sha256": digest_bytes(payload)},
        )
        return replace(report, report_artifact_uri=uri)
