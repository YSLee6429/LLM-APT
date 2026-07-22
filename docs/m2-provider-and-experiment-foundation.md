# M2 Provider and Experiment Foundation

Version `0.3.0a1` is the first M2 vertical slice. It makes provider calls and experiment plans
explicit, typed, reproducible, and testable without requiring a paid API credential.

## Provider boundary

`ModelProvider` remains the only application-facing generation contract. A
`ProviderRegistry` maps fixed local keys to adapters; clients cannot submit an endpoint, API
key, or model name in a request. The registry always exposes the deterministic `local`
provider. An external OpenAI-compatible provider is added only when all settings are present
and `LLMAPT_EXTERNAL_MODEL_CALLS_ENABLED=true`.

The HTTP adapter fixes the model identity, endpoint, authorization header, message structure,
and `stream=false`. Only these generation parameters are accepted:

- `temperature`
- `top_p`
- `max_tokens`
- `seed`
- `frequency_penalty`
- `presence_penalty`
- `stop`

Authentication failures, rate limits, transport errors, non-success HTTP responses, malformed
schemas, and empty output are separated from model-generated program verdicts.

## Source extraction

Model prose is preserved as a raw-response digest. Compilation receives only the deterministic
candidate selected by these rules:

1. prefer exactly one fenced block whose label matches the requested language;
2. otherwise accept exactly one fenced block;
3. when no fence exists, treat the trimmed response as source;
4. reject ambiguous, empty, or oversized candidates.

## Experiment manifest

Each plan records a UUID, problem and test-suite digests, immutable model identity, prompt
template version, seed, repetitions, and sorted model parameters. `plan_digest` excludes UUID
and creation time, so equivalent plans have the same digest while remaining separate records.

The initial repository is deliberately in memory and API responses carry
`ephemeral_storage=true`. PostgreSQL persistence and distributed scheduling are the next M2
slice.

## API

```text
GET  /api/v1/providers
POST /api/v1/providers/generate
POST /api/v1/experiments/plan
GET  /api/v1/experiments/{experiment_id}
```

The local provider can be exercised without credentials:

```bash
curl -sS http://127.0.0.1:8000/api/v1/providers
curl -sS -X POST http://127.0.0.1:8000/api/v1/providers/generate \
  -H 'content-type: application/json' \
  -d '{"provider_key":"local","prompt":"solve","language":"cpp"}'
```

## External configuration

```dotenv
LLMAPT_EXTERNAL_MODEL_CALLS_ENABLED=true
LLMAPT_MODEL_PROVIDER_KEY=external
LLMAPT_MODEL_PROVIDER_NAME=openai-compatible
LLMAPT_MODEL_NAME=<provider-model-id>
LLMAPT_MODEL_REVISION=<optional-revision>
LLMAPT_MODEL_API_ENDPOINT=https://<provider-host>/v1/chat/completions
LLMAPT_MODEL_API_KEY=<secret>
LLMAPT_MODEL_TIMEOUT_SECONDS=60
```

Do not commit `.env`. Production deployments must inject the key from a secret manager and
must not expose the generation endpoint until authentication, quotas, and audit policy are in
place.
