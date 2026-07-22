# Contributing

1. Create a focused branch from `main`.
2. Add or update tests for every behavior change.
3. Run `ruff`, `mypy`, and `pytest` locally, then run frontend lint, type checking, tests,
   and the production build.
4. Keep adapters behind application ports and domain code free of web-framework imports.
5. Do not commit secrets, generated artifacts, model responses, or unpublished datasets.

All contributors must follow the security policy and preserve reproducibility metadata.
