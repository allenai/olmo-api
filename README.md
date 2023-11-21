# olmo-api

The HTTP API used by http://olmo.allen.ai.

## Contributing

### Getting Started

The API depends on [InferD](https://github.com/allenai/inferd). To start a local
server, follow these steps:

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

There are some end-to-end tests. They are slow. You can run them like so:

```
docker compose exec api pytest
```

## More Documentation

- [Database Access](./docs/db.md)

