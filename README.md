# olmo-api

The HTTP API used by http://olmo.allen.ai.

## Contributing

### Getting Started

The API depends on [InferD](https://github.com/allenai/inferd). You'll need to forward a local
port to the current InferD service to get things working.

1. Start by connecting to the Kuberenetes cluster:

    ```
    gcloud container clusters get-credentials \
        --project ai2-inferd \
        --region us-central1 \
        inferd-prod
    ```

2. Then forward `10000` from your host to the InferD service:

    ```
    kubectl port-forward -n inferd service/system 10000
    ```

3. Then generate a local `config.json` file:

    ```
    ./bin/bootstrap
    ```

4. Next open another terminal and launch the application like so:

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

