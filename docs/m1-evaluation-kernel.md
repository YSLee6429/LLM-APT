# M1 Reproducible Evaluation Kernel

## Scope

M1 establishes deterministic evaluation semantics without running untrusted model output on
the control-plane host. It includes the data model, orchestration, evidence format, mock
adapters, public validation schema, and runner boundary required by later milestones.

## Problem contract

`ProblemSpec` is immutable and requires:

- a stable problem identifier, title, statement, and language;
- at least one uniquely identified test case;
- positive time, memory, process, and output limits;
- one explicit output comparison policy;
- SHA-256 digests for the statement and ordered test suite.

The public JSON representation is exposed by OpenAPI and accepted by
`POST /api/v1/problems/validate`. Text inputs and outputs are encoded as UTF-8 when converted
to the domain model.

## Output policies

- `exact`: newline style is canonicalized; all remaining bytes must match.
- `trim_trailing_whitespace`: spaces and tabs at line endings plus final empty lines are
  ignored.
- `token`: tokens separated by any whitespace must match exactly.

The judge does not use an LLM. Runner facts are classified in this order:

1. infrastructure error;
2. time limit exceeded;
3. memory limit exceeded;
4. output limit exceeded;
5. non-zero exit code;
6. output comparison.

## Runner contract

The `Sandbox` port separates compilation from execution:

```text
compile(source, language, limits) -> CompilationResult
execute(artifact_token, arguments, stdin, limits) -> ExecutionResult
```

A successful compilation returns an opaque token. The control plane cannot interpret the
token and must pass it back to the same runner. Generated source and model credentials must
never be mounted together in the future execution plane.

`ScriptedSandbox` implements this contract from predefined results and never starts a process.
It is suitable for deterministic unit, API, and CI tests, but it is not a production sandbox.

## Reproducibility and evidence

Every run stores a manifest containing model identity, random seed, prompt template version,
and a configuration digest. The digest covers:

- prompt content;
- problem statement and ordered test suite;
- language and output policy;
- every resource limit;
- model parameters and random seed.

The evaluation report references the raw model response, candidate source, compiler
diagnostics, per-case stdout and stderr, and its own serialized report artifact. Case evidence
contains input, expected output, actual output, and stderr SHA-256 digests.

## Demonstration

The API and CLI provide three deterministic scenarios:

```bash
uv run llmapt mock-evaluate --scenario accepted
uv run llmapt mock-evaluate --scenario wrong_answer
uv run llmapt mock-evaluate --scenario compile_error
```

The API endpoint is `POST /api/v1/evaluations/mock`. Its artifacts are explicitly marked
ephemeral because the M1 demonstration uses an in-memory artifact store. Persistent adapters
and real provider integrations belong to the closed-loop milestone.

`GET /health/ready` performs live checks against PostgreSQL, RabbitMQ, Redis, and MinIO. It
returns HTTP 503 with component-level `unavailable` states if any dependency cannot be reached.
