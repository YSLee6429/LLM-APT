# M2 Closed-Loop Completion

Version `0.3.0` completes the research-grade M2 loop from a seed problem to reproducible execution
evidence. The pipeline remains conservative: a model failure is published only after a trusted
Oracle, an explicit human admission, isolated execution, and repeated matching observations.

## End-to-end flow

1. A registered mutation operator proposes and persists a candidate.
2. A server-controlled Oracle verifies parent binding and recomputes every expected output.
3. An authenticated reviewer approves semantics and moves the candidate to `ready`.
4. The selected Provider generates source independently for every repetition.
5. The control plane sends source and test input through the typed HTTP Sandbox boundary.
6. The Runner compiles C++20 and executes the artifact under time, address-space, process, output,
   container memory, CPU, PID, filesystem, capability, and network restrictions.
7. The deterministic judge classifies each execution. Infrastructure failure is excluded from
   model-failure evidence.
8. Matching verdict, source digest, failing case, and actual-output digest across at least two
   repetitions upgrades evidence to `REPRODUCIBLE_FAILURE`.
9. For stable WA, token delta debugging proposes smaller inputs; the trusted Oracle rejects illegal
   candidates and supplies the new expected output before the candidate binary is rerun.
10. PostgreSQL stores the private report and the candidate advances to `evaluated`.

## Runner boundary

The local Runner is a separate container and is not exposed on a host port. Its only network is the
Docker `internal` runner network shared with the API. It runs as UID 10002, drops all capabilities,
uses `no-new-privileges`, a read-only root filesystem, executable `/work` tmpfs, non-executable
`/tmp`, 64 PID maximum, 512 MiB container memory, and one CPU. Candidate processes additionally
receive `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_NPROC`, `RLIMIT_FSIZE`, and zero core-dump limits.

Compiler processes are trusted tooling but parse untrusted source, so they remain inside the same
restricted Runner. Artifacts have random UUID paths and are pruned by count and age. The local
boundary is suitable for development and reproducible research; M4 replaces it with per-job gVisor
or equivalent stronger isolation for hostile multi-tenant production.

## Evidence privacy

Private records retain the raw model response, extracted source, actual output, and minimized input
needed for audit and reproduction. Public API projections expose SHA-256 digests, verdicts, sizes,
case IDs, and attempt counts. They never return raw hidden test input, generated source, Runner
artifact tokens, or actual output bytes.

## API

```text
POST /api/v1/mutations/{candidate_id}/review
POST /api/v1/closed-loop/run
GET  /api/v1/closed-loop/{report_id}
```

The review endpoint requires `X-Review-Token`; deployment must replace the local example secret.
M3 will replace this shared-token review mechanism with authenticated users, projects, and roles.

## M2 completion boundary

M2 is a closed-loop prototype, not the final commercial multi-tenant service. It intentionally
leaves user authentication, dashboards, quotas, report exports, distributed runner pools,
transactional outbox/unit-of-work hardening, gVisor, Kubernetes, and long-term audit retention to
M3 and M4. These limitations do not invalidate M2 evidence semantics or its local reproducibility.
