# Architecture

LLM-APT uses a modular control plane with distributed workers and a separate execution
plane. The initial repository is a modular monolith so domain boundaries can stabilize
before any service is split out.

```text
Web / CLI / SDK
       |
    FastAPI
       |
Application services and ports
       |
Domain model and state machines
       |
Adapters: PostgreSQL, RabbitMQ, Redis, S3/MinIO, model providers
       |
Isolated execution plane for generated code
```

## Dependency rule

Dependencies point inward. Domain modules import only the Python standard library.
Application modules may import domain modules. Infrastructure and delivery modules
implement application ports. The domain never imports FastAPI, SQLAlchemy, Celery, or a
model-provider SDK.

## Trust boundaries

- Model responses and generated source code are untrusted.
- API credentials remain in the control plane and are never mounted into runner jobs.
- A wrong-answer claim requires legal input, trusted expected output, actual output, and
  repeatability evidence.
- Infrastructure failures are not counted as model failures.

## M1 evaluation flow

```text
ProblemDefinition -> domain validation -> ProblemSpec
ModelProvider -> immutable model identity + raw response artifact
Sandbox.compile -> compilation token or compile error
Sandbox.execute(test case) -> execution facts
Deterministic judge -> verdict + digests + artifact references
EvaluationReport -> report artifact
```

The M1 `ScriptedSandbox` is a contract test double. It never invokes a compiler or executes
source code. This makes the control-plane evaluation logic testable before a hardened
execution plane is introduced.

## M2 provider and experiment flow

```text
ProblemDefinition + provider key + parameters
                  |
          ExperimentPlanner
                  |
   canonical ExperimentManifest + plan digest
                  |
       explicit ProviderRegistry
          /                 \
 deterministic local   configured external adapter
          \                 /
              ModelResponse
                  |
 deterministic source extraction
                  |
       M1 evaluation / future runner
```

Provider request data never controls endpoints, credentials, or model identity. Those values
come from process settings and are resolved by the infrastructure factory. External calls are
disabled unless explicitly enabled.

Version `0.3.0a2` persists manifests and lifecycle state in PostgreSQL. The API records a queued
state before publishing an explicitly identified Celery task; publication failures are converted
to a failed state. The worker accepts only queued or already-running experiments, performs an
idempotent preparation check, and records success. Celery delivery is at least once, so the
state machine and stable task identifier are the correctness boundary. A transactional outbox is
reserved for production hardening.

Mutation operators are registered domain operations rather than arbitrary model instructions.
Every candidate retains its parent digests and seed and is marked as requiring trusted oracle
validation. A preview is never equivalent to a valid benchmark or reported model failure.

## Trusted Oracle admission

```text
untrusted mutation request
          |
  persisted candidate (generated)
          |
 structural gate (structure_validated)
          |
server registry resolves key + version + parent binding
          |
recompute expected output for every test
      /                         \
all match                     mismatch / bad binding
      |                              |
oracle_validated                  rejected
```

Clients can select only an Oracle key. They cannot supply its implementation, parent binding, or
version. Validation stores input, expected-output, and actual-output digests plus sanitized reason
codes. The built-in Oracle executes trusted packaged logic only; uploaded or generated source is
still never executed in the control plane. Statement-changing candidates require a later human
semantic review even after their test outputs pass the Oracle.

## M2 closed-loop execution

```text
oracle_validated -> authenticated review -> ready
       -> model generation (repeated)
       -> HTTP Sandbox port
       -> internal Runner: C++20 compile + bounded execution
       -> deterministic verdict signatures
       -> reproducible evidence or inconclusive result
       -> token delta reduction with Oracle legality checks
       -> private PostgreSQL report -> evaluated
```

The Runner is the only component that invokes a compiler or candidate binary. It is attached only
to an internal Docker network, runs as UID 10002 with all Linux capabilities dropped, uses a
read-only root filesystem and executable tmpfs, and is bounded by container and per-process limits.
The API sends a shared internal token and exposes neither the Runner port nor its artifact tokens.

Evidence reports retain raw model response, extracted source, actual output, and minimized input
inside the private persistence record. Public API responses expose digests and sizes but omit raw
hidden inputs, candidate source, and actual output bytes. Infrastructure failures never upgrade to
model-failure evidence. Two identical generation/execution signatures are required for
`REPRODUCIBLE_FAILURE`.
