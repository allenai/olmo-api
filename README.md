# olmo-api

The HTTP API used by http://playground.allenai.org

## Contributing

### Getting Started

To start a local server, follow these steps:

1. Generate a local `config.json` file:

    ```
    ./bin/bootstrap
    ```

2. Next open another terminal and launch the application like so:

    ```
    docker compose up --build --watch
    ```

### Adding a new package
We use uv's workspaces to split code into larger chunks. 

To add a new package, cd to `packages` and run `uv init --lib --package package-name`. Make sure you run `uv add package-name --package <DEPENDENT_PACKAGE>` for any packages that depend on it.

To add a new app, cd to `apps` and run `uv init app-name`.

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

On macOS, ensure you have `homebrew` installed then run `brew install ffmpeg`

Change `db.conninfo` in `config.json` to "postgres://app:llmz@127.0.0.1:5555/llmx?sslmode=disable"

start the postgres container with `docker compose up db`

make sure you're in the venv by running `.venv/bin/activate`

Start the server by running `FLASK_APP=app.py python -m flask run -p 8000`

Note: If you run e2e tests with a local server it's possible for the containers and local server to be out of sync. Make sure you run e2e tests in the docker-compose

### Debugging the API in VSCode:

Ensure you have the [Python Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) installed.

Instead of starting the server with the `python` command above, launch the `Python Debugger: Flask` debug task in VSCode's debug menu.

## Regenerating infinigram-api-client

run `openapi-python-client generate --url https://infinigram-api.allen.ai/openapi.json --overwrite`

copy the `infini_gram_api_client` folder from the generated code into `src/attribution/infini_gram_api_client`
