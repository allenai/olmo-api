default:
  just --list

install:
  uv sync --all-packages --all-groups

test:
  ENV=test FLASK_CONFIG_PATH="./test.config.json" uv run pytest --ignore ./apps/flask-api/e2e --ignore ./apps/api/e2e  --ignore ./apps/evaluations

test-e2e: test-e2e-flask test-e2e-api
  
test-e2e-flask:
  ENV=test FLASK_CONFIG_PATH="./test.config.json" uv run pytest ./apps/flask-api/e2e

test-e2e-api:
  ENV=test uv run pytest ./apps/api/e2e

# Formatting, linting, type checking
verify: format lint type-check

format:
  uv run ruff format

lint *ARGS:
  uv run ruff check {{ARGS}} --exclude ./apps/flask-api

type-check-flask:
  uv run mypy apps/flask-api

type-check-api:
  uv run mypy apps/api packages

type-check: type-check-api type-check-flask

dev:
  ENV=development uv run fastapi dev ./apps/api/main.py --port 8888
