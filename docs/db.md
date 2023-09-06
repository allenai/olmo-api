# Database

The API uses a [Google Cloud SQL database](https://console.cloud.google.com/sql/instances/llmx-api/users?project=ai2-reviz)
for persistence.

## Connecting to the Database

To connect to the production database [install and configure the `gcloud` command](https://cloud.google.com/sdk) and run:

```bash
gcloud beta sql connect llmx-api --project ai2-reviz
```

The password for the `postgres` user can be found in 1Password.

If you can't connect to the database or don't have access to the 1Password vault, send a note to
[reops@allenai.org](mailto:reops@allenai.org).


## Schema Migrations

> [!WARNING]
> If you're executing migrations in production you could break the public API, so tread carefully.

To run schema migrations:

1. Connect to the database:

    ```
    gcloud beta sql connect llmx-api --project ai2-reviz --port 5555
    ```

   When prompted for a password don't enter one, but leave the program running (it opens a tunnel).

2. Obtain the password for the `postgres` user from 1Password.

3. In a new terminal, run the command below, replacing `$PASSWD` with the value from the previous step.

    ```bash
    psql "postgres://postgres:$PASSWD@localhost:5555/llmx?sslmode=disable" < schema/schema.sql
    ```

