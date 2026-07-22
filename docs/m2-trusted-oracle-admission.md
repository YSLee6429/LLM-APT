# M2 Trusted Oracle Admission

Version `0.3.0a3` implements the first executable candidate-admission gate. It validates expected
outputs using trusted, packaged Oracle functions while preserving the rule that generated or
uploaded source never executes in the control plane.

## Trust model

An Oracle is registered by the server and has an immutable key, version, parent problem ID,
parent statement digest, and language. A request contains only a persisted candidate ID and an
Oracle key. It cannot provide source code, an endpoint, credentials, a replacement implementation,
or a different binding.

The initial `builtin.double` Oracle is intentionally small and auditable. It is bound to the exact
statement in `examples/problems/double.json`. Additional production Oracles must be reviewed,
versioned, deterministic, resource bounded, and registered through deployment configuration or a
signed plugin package rather than request data.

## Admission sequence

1. `POST /api/v1/mutations/propose` persists the candidate in `generated` state.
2. `POST /api/v1/oracles/validate` advances it to `structure_validated`.
3. The registry verifies the parent problem, parent statement digest, and language binding.
4. The Oracle recomputes output for every persisted test input under input/output size limits.
5. The deterministic judge applies the candidate's declared output policy.
6. An immutable report stores Oracle identity, candidate digests, case digests, match flags, and a
   sanitized reason code.
7. A complete match advances the candidate to `oracle_validated`; mismatch or invalid input moves
   it to `rejected`; an unexpected Oracle exception moves it to `quarantined`.

A repeated request for an already validated candidate returns its persisted report instead of
executing the Oracle again.

## Persistence

Alembic revision `20260721_0002` creates `mutation_candidates` and `oracle_validations`.
Problem bytes are stored as hexadecimal strings inside the JSON snapshot so binary test data is
round-trippable without relying on database text encoding. Candidate status updates use a
conditional database update and the domain transition table.

The report save and terminal state update currently use separate transactions. A crash between
them cannot falsely admit a candidate—the state remains `structure_validated`—but it may leave an
extra audit report. A later unit-of-work/outbox hardening slice will make the pair atomic.

## Semantic limitation

Oracle output agreement proves that the stored expected outputs match the registered reference
behavior on the stored inputs. It does not mathematically prove that a changed natural-language
statement is unambiguous or that the Oracle implements every intended requirement. In particular,
`boundary_clause` candidates remain subject to human semantic review before `ready` state.

## API

```text
POST /api/v1/mutations/propose
GET  /api/v1/mutations/{candidate_id}
GET  /api/v1/mutations/{candidate_id}/state
GET  /api/v1/oracles
POST /api/v1/oracles/validate
```
