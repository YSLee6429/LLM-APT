# Roadmap

## M0: Foundation — complete

- Package, API, worker, configuration, logs, local infrastructure, tests, and CI.

## M1: Reproducible evaluation kernel — complete

- Problem schema, model mock, C++ runner contract, test cases, verdicts, and artifacts.
- Deterministic output policies, configuration digests, case evidence, mock API, and CLI.

## M1.5: Interactive evaluation workbench — complete

- React 19 and TypeScript workbench with live infrastructure readiness.
- Editable problem validation and deterministic AC, WA, and CE evidence demonstrations.
- Production Nginx container, same-origin API proxy, responsive layout, and dark/light theme.
- Frontend lint, strict type checking, component tests, production build, and HTTP acceptance.

## M2: Closed-loop prototype — complete

- Completed in `0.3.0a1`: provider registry, OpenAI-compatible adapter, source extraction,
  experiment manifests, plan digests, and the local generation/planning API.
- Completed in `0.3.0a2`: PostgreSQL experiment persistence, Alembic migration, explicit
  lifecycle transitions, Celery dispatch/preparation, and three deterministic mutation previews
  guarded by mandatory oracle validation.
- Completed in `0.3.0a3`: persisted mutation candidates, server-registered trusted Oracle
  identities, output recomputation, immutable validation reports, and candidate admission or
  rejection through the existing state machine.
- Completed in `0.3.0`: authenticated human admission, network-internal C++20 Runner, real
  compile/execute verdicts, repeated generation and execution, reproducible-failure evidence,
  deterministic counterexample reduction, persisted private evidence, and closed-loop APIs.

## M3: Evaluation website expansion — complete

- Signed local authentication and admin/reviewer/researcher/viewer roles.
- Research projects, resource links, and model profiles.
- Experiment/candidate dashboard, evidence review, and JSON/Markdown/CSV report exports.
- Responsive React workspace with restrained light/dark presentation and lazy-loaded modules.

## M4: Production hardening — future work

- Multi-tenancy, quotas, gVisor-backed runners, audit retention, observability, and
  Kubernetes deployment.
