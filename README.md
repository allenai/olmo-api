# olmo-api

The HTTP API used by http://playground.allenai.org

## Contributing

### Getting Started

The API depends on [InferD](https://github.com/allenai/inferd).
To start a local server, follow these steps:

1. Generate a local `config.json` file:

    ```
    ./bin/bootstrap
    ```

2. Next open another terminal and launch the application like so:

    ```
    docker compose up --build
    ```

### Reset Schema

The API uses a local database for persistence. If you'd like to delete all
data or reapply the schema, run:

```
docker compose down --volumes && docker compose up --build
```

### Tests

There are some end-to-end tests. Most call the `olmo-7b-chat` model, and are therefore fast.
One test requires logprobs, which only the `tulu2` model currently provides (see [allenai/inferd-olmo#1](https://github.com/allenai/inferd-olmo/issues/1)).

To run them, execute:

```
docker compose exec api pytest
```

## More Documentation

- [Database Access](./docs/db.md)

## Running the API outside of Docker:
Change `db.conninfo` in `config.json` to "postgres://app:llmz@localhost:5555/llmx?sslmode=disable"

start the postgres container with `docker compose start db`

make sure you're in the venv by running `.venv/bin/activate`

Start the server by running `FLASK_APP=app.py python -m flask run -p 8000`

Note: If you run e2e tests with a local server it's possible for the containers and local server to be out of sync. Make sure you run e2e tests in the docker-compose

### Debugging the API in VSCode:
Ensure you have the [Python Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) installed.

Instead of starting the server with the `python` command above, launch the `Python Debugger: Flask` debug task in VSCode's debug menu.

## Add new model
Make sure the host information that the new model is deployed on. Currently, we have InferD, Modal, and TogetherAI. Once the information is confirmed, open `config.json` and add settings for the new model under the "available_models" field of the corresponding host.
After adding, relaunch olmo-api on your localhost. The new model should appear in the dropdown on Olmo UI. Try to send a prompt to verify it works.
Once localhost is working goes to marina and search for olmo_api and update config.json under secret. Then trigger a manual deployment to verify prod working.