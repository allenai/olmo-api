# olmo-api

The HTTP API used by http://olmo.allen.ai.

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

### Creating short-term access links to AI2 Playground
You can create short-term links for external users to gain one-time access to the AI2 Playground. 

First, you will need to be added as an admin [here](https://marina.apps.allenai.org/a/olmo-api/).

Next, go to [whoami](https://olmo-api.allen.ai/v3/whoami) and grab your `token` from the cookies.

Then, execute the following script from the root of the repo to generate a link for a specific user email: 

`TOKEN=<your whoami token here> ./bin/mkinvite <user_email@domain.com>`

You can update the details of the produced email format to swap the default contact email out with your own. 

By default, the link will expire in 7 days, but you can change the expiration time with the `--expires` flag.
