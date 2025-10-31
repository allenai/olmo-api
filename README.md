# olmo-api

The HTTP API used by http://playground.allenai.org

**Framework:** FastAPI 0.116+ with Python 3.11+

## Features

- **FastAPI** with async/await support for high performance
- **Pydantic V2** for data validation and serialization
- **OpenAPI/Swagger** automatic documentation at `/docs`
- **Auth0** JWT authentication
- **PostgreSQL** database with SQLAlchemy ORM
- **Google Cloud Storage** for file uploads
- **OpenTelemetry** distributed tracing
- **Docker Compose** for local development

## Contributing

### Getting Started

Install ffmpeg:
On OSX, ensure you have `homebrew` installed then run `brew install ffmpeg`

To start a local server, follow these steps:

1. Generate a local `config.json` file:

    ```
    ./bin/bootstrap
    ```

2. Next open another terminal and launch the application like so:

    ```
    docker compose up --build
    ```

3. The API will be available at:
   - **API:** http://localhost:8000
   - **OpenAPI Docs:** http://localhost:8000/docs
   - **Health Check:** http://localhost:8000/health

### Reset Schema

The API uses a local database for persistence. If you'd like to delete all
data or reapply the schema, run:

```
docker compose down --volumes && docker compose up --build
```

### Tests

To run them, execute:

```
docker compose exec api pytest -m "not integration"
```

### Type check

To check all types run:

```bash
mypy . --config ./pyproject.toml
```

## More Documentation

-   [Database Access](./docs/db.md)
-   [Model Configuration](./docs/model-config.md)

## Running the API outside of Docker:

1. Change `db.conninfo` in `config.json` to:
   ```
   "postgres://app:llmz@127.0.0.1:5555/llmx?sslmode=disable"
   ```

2. Start the postgres container:
   ```bash
   docker compose start db
   ```

3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

4. Start the FastAPI server:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

**Note:** If you run e2e tests with a local server it's possible for the containers and local server to be out of sync. Make sure you run e2e tests in docker-compose.

### Debugging the API in VSCode:

Ensure you have the [Python Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) installed.

Create a launch configuration in `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app:app", "--reload"],
      "jinja": true,
      "env": {
        "FLASK_CONFIG_PATH": "./config.json"
      }
    }
  ]
}
```

Then launch the "FastAPI" debug task in VSCode's debug menu.

## Regenerating infinigram-api-client

run `openapi-python-client generate --url https://infinigram-api.allen.ai/openapi.json --overwrite`

copy the `infini_gram_api_client` folder from the generated code into `src/attribution/infini_gram_api_client`
