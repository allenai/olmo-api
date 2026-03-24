# olmo-api

The HTTP API used by http://playground.allenai.org

## Contributing

### Getting Started

To start a local server, run:

    ```sh
    sh ./bin/bootstrap
    ```

then run:

    ```sh
    docker compose up --build --watch
    ```
    
#### Running without Docker
This project uses [uv](https://docs.astral.sh/uv). To run it locally, follow their [installation guide](https://docs.astral.sh/uv/#installation).

After uv is installed, run `just install` at the root of this project.

### Adding a new package
We use uv's workspaces to split code into larger chunks. 

To add a new package, cd to `packages` and run `uv init --lib --package package-name`. Make sure you run `uv add package-name --package <DEPENDENT_PACKAGE>` for any packages that depend on it.

To add a new app, cd to `apps` and run `uv init app-name`.

### Configuration and secrets

### FastAPI
FastAPI app uses pydandantic settings to load settings, it has default values set in `./apps/api/src/api/config.py` and loads
environment variables from `.env`, `.env.local`, `.env.${ENV}` and `.env.${ENV}.local`, with `.local` files being ignored

Public configuration variables should be stored in non-`gitignore`d configs, with env agnostic configs in `.env`.

Secrets should be stored in `.env.local` (or `.env.${ENV}.local`) file.

### Reset Schema

The API uses a local database for persistence. If you'd like to delete all
data or reapply the schema, run:

```
docker compose down --volumes && docker compose up --build
```

### Tests

To run the unit tests, run:

```bash
just test
```

### Type check

To check types:

```bash
just type-check
```

### Formatting / Linting

To run the formatter / linter:

```bash
just format
```

To just check without making changes to the files:
```bash
uv run ruff format --check
```

To check for linting issues in fastapi:

```bash
just lint
```

## More Documentation

-   [Database Access](./docs/db.md)
-   [Model Configuration](./docs/model-config.md)

## Running the API outside of Docker:

On macOS, ensure you have `homebrew` installed then run `brew install ffmpeg`

start the postgres container with `docker compose up db`

Make sure you've installed packages and activated the environment with `just install`

Start the server by running `just dev`

### Debugging the API in VSCode:

Ensure you have the [Python Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) installed.

Instead of starting the server with the `python` command above, launch the `Python Debugger: FastAPI` debug task in VSCode's debug menu.

## Regenerating infinigram-api-client

run `openapi-python-client generate --url https://infinigram-api.allen.ai/openapi.json --overwrite`

copy the `infini_gram_api_client` folder from the generated code into `src/attribution/infini_gram_api_client`
