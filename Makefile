.PHONY: sync lint format-check typecheck test check api infra-up infra-down

sync:
	uv sync --locked --all-groups

lint:
	uv run ruff check .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy src

test:
	uv run pytest

check: lint format-check typecheck test
	docker compose config --quiet

api:
	uv run uvicorn llmapt.main:app --reload

infra-up:
	docker compose up -d postgres rabbitmq redis minio

infra-down:
	docker compose down
