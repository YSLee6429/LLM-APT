# M2 Persistence, Dispatch, and Mutation Preview

Version `0.3.0a2` turns the initial experiment plan into a durable control-plane record and adds
the first bounded mutation operators. This slice deliberately stops before executing generated
programs or claiming benchmark failures.

## Durable experiment lifecycle

The initial Alembic revision creates the `experiments` table. It stores the immutable manifest,
canonical parameter object, plan digest, lifecycle state, task identifier, timestamps, and a
sanitized failure code. Development and production use the PostgreSQL repository; tests use the
same port with an in-memory adapter.

Allowed transitions are checked in both the domain state machine and the repository's atomic
conditional update:

```text
planned -> queued -> running -> succeeded
   |          |          |
   |          |          +-> failed -> queued (explicit retry)
   |          +-> failed
   +-> cancelled
queued -> cancelled
```

The API records `queued` before publishing the Celery message. A broker publication failure
changes that record to `failed`. Celery uses at-least-once delivery, so workers use the persisted
state and stable task ID to make repeated preparation harmless. A transactional outbox remains a
future hardening item for eliminating the small process-crash gap between database commit and
broker publication.

## API sequence

```text
POST /api/v1/experiments/plan
GET  /api/v1/experiments/{experiment_id}
GET  /api/v1/experiments/{experiment_id}/state
POST /api/v1/experiments/{experiment_id}/enqueue
```

The preparation task verifies that the manifest can be loaded and advances the state to
`succeeded`. It is infrastructure plumbing, not a model evaluation result.

## Mutation preview operators

`POST /api/v1/mutations/preview` accepts one registered operator:

- `test_order_rotation` deterministically rotates at least two tests from the supplied seed.
- `boundary_clause` appends an explicit, length-bounded boundary statement.
- `output_policy_exact` tightens a non-exact comparison policy to exact bytes.

Each response includes the parent problem identifier, statement and test-suite digests, the
random seed, operator notes, and `requires_oracle_validation=true`. The boundary operator changes
problem semantics and therefore cannot be admitted to an experiment until a trusted reference
solution and legal-input validator confirm the new statement and test set. The other operators
also retain the oracle gate so a preview can never be confused with reviewed evidence.

## Operations

The API image runs `alembic upgrade head` before starting Uvicorn. The worker waits for the API
health check, which ensures schema migration has completed before task consumption begins.

Useful checks:

```bash
docker compose exec api alembic current
docker compose ps
uv run pytest --cov=src/llmapt --cov-fail-under=85
```
