# Changelog

All notable project changes are recorded in this file.

## 0.4.0 - 2026-07-21

### Added

- PBKDF2 password verification and HMAC-SHA256 signed local access tokens with bounded expiry.
- Persistent workspace users, research projects, resource links, and model profiles through
  Alembic revision `20260721_0004`.
- Authenticated dashboard projections for experiments, candidates, verdicts, and stable failures.
- Public evidence review with project filtering and JSON, Markdown, and CSV report exports.
- Authenticated reviewer identity support while retaining the M2 shared-token compatibility path.
- Complete React workspace with login, dashboard, projects, profiles, experiment/candidate index,
  evidence drawer, exports, problem lab, system status, responsive layout, and light/dark themes.
- Lazy-loaded frontend modules and deterministic local M3 acceptance records.

### Boundary

- This release is a single-workspace, local research platform. Multi-tenancy, quotas, gVisor,
  Kubernetes, long-term audit retention, and commercial operations remain M4 future work.

## 0.3.0 - 2026-07-21

### Added

- Authenticated, auditable human review gate from `oracle_validated` to `ready`.
- Network-internal C++20 Runner with compile and execution APIs and an HTTP Sandbox adapter.
- Real CE, WA, runtime, timeout, and output-limit classification from isolated process facts.
- Repeated model generation/execution with stable-signature reproducibility upgrading.
- Deterministic token delta reduction that retains only Oracle-legal failing inputs.
- Private closed-loop reports containing raw response/source/output evidence and public digest-only
  API projections.
- Candidate review and closed-loop report persistence through Alembic revision `20260721_0003`.
- Runner readiness in the API dependency health report.

### Security

- Runner has no published port or external network route, runs non-root, drops all capabilities,
  and uses read-only root, executable tmpfs, PID, memory, CPU, process, output, and time limits.
- Runner requests require an internal shared token; human review requires a separate review token.
- Hidden inputs, raw generated source, and actual output bytes are excluded from public reports.
- Infrastructure errors become retry state or inconclusive evidence, never model failures.

## 0.3.0a3 - 2026-07-21

### Added

- Durable mutation-candidate and Oracle-validation records with Alembic revision `20260721_0002`.
- Candidate proposal, retrieval, lifecycle, Oracle catalog, and Oracle validation APIs.
- Server-controlled Oracle registry with immutable key, version, parent statement, and language
  bindings.
- Per-case recomputation records containing input and output digests and sanitized reason codes.
- Idempotent successful validation reads through the candidate admission state.

### Security

- API callers cannot upload an Oracle implementation or alter its identity and parent binding.
- Binding mismatches and incorrect expected outputs reject candidates before evaluation.
- Unexpected trusted-Oracle failures quarantine candidates without exposing exception details.
- Generated and user-uploaded source remains unexecuted in the control plane.

## 0.3.0a2 - 2026-07-21

### Added

- PostgreSQL experiment repository with an initial Alembic migration.
- Durable planned, queued, running, succeeded, failed, and cancelled lifecycle records.
- Celery experiment dispatch with stable task identifiers and idempotent preparation.
- Experiment-state and enqueue API endpoints.
- Deterministic test-order, boundary-clause, and exact-output mutation previews.

### Security

- Every mutation preview is explicitly marked as requiring trusted oracle validation.
- A generated mutation cannot become evaluation evidence solely through the preview endpoint.
- Broker publication errors are persisted as failed lifecycle state without exposing credentials.

## 0.3.0a1 - 2026-07-21

### Added

- Immutable experiment manifests with canonical parameters and stable plan digests.
- Explicit model-provider registry with a deterministic local provider.
- OpenAI-compatible HTTP adapter with parameter allowlisting and classified remote failures.
- Candidate source extraction from plain responses and language-matched Markdown fences.
- Provider catalog, controlled generation, experiment planning, and experiment retrieval APIs.
- In-memory experiment repository boundary for the first M2 vertical slice.
- Non-secret provider diagnostics through the CLI.

### Security

- External model calls remain disabled by default and credentials never appear in API responses.
- Provider selection is restricted to the configured registry; request data cannot set endpoints,
  credentials, messages, model identity, or streaming mode.

## 0.2.1 - 2026-07-19

### Added

- React 19, TypeScript, Vite, and Ant Design evaluation workbench.
- Live component readiness, editable Problem Schema validation, and AC/WA/CE evidence views.
- Vitest API and component tests with strict ESLint and TypeScript quality gates.
- Multi-stage Node/Nginx web image and same-origin reverse proxy for API documentation and calls.

### Changed

- Docker Compose now exposes the complete product at `http://127.0.0.1:3000`.
- Roadmap records the M1.5 interactive workbench without changing M2 research scope.

## 0.2.0 - 2026-07-19

### Added

- Immutable problem, resource-limit, test-case, case-result, and report models.
- Stable SHA-256 statement, test-suite, prompt, configuration, and evidence digests.
- Explicit exact, trailing-whitespace, and token output comparison policies.
- Compile-once/run-many sandbox port and deterministic verdict classification.
- Evaluation service with model identity checks and auditable artifact references.
- Deterministic model, sandbox, run repository, and artifact store adapters.
- Problem validation and mock evaluation API endpoints.
- AC, WA, and CE CLI demonstration scenarios.
- Live PostgreSQL, RabbitMQ, Redis, and MinIO readiness checks.
- Architecture dependency tests and M1 documentation.

### Security

- Generated source remains unexecuted in M1; scripted runner facts test the boundary.
- Infrastructure errors are classified separately from model failures.

## 0.1.0 - 2026-07-18

- Initial package, API, worker, local infrastructure, quality gates, and CI foundation.
