default:
  just --list

install:
  uv sync --all-packages --all-groups

test:
  FLASK_CONFIG_PATH="./test.config.json" uv run pytest --ignore ./apps/flask-api/e2e --ignore ./apps/api/e2e

test-e2e: test-e2e-flask test-e2e-api
  
test-e2e-flask:
  FLASK_CONFIG_PATH="./test.config.json" uv run pytest ./apps/flask-api/e2e

test-e2e-api:
  uv run pytest ./apps/api/e2e

# Formatting, linting, type checking
verify: format lint type-check

format:
  uv run ruff format

lint *ARGS:
  uv run ruff check {{ARGS}} --exclude ./apps/flask-api

type-check:
  uv run mypy apps packages