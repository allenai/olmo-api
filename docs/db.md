# Database

## Connecting to the Database

### Local

The Postgre listens on port `5432` by default. However, based on `docker-compose.yaml`, the port is forwarded to `5555` on your localhost. If you would like to connect to the DB, make sure the docker instance of Olmo API is running your local, then run below command:
```bash
docker compose exec db psql --user=postgres llmx
```
If you have `psql` command in your terminal, you can also run:
```bash
psql "postgres://app:llmz@localhost:5555/llmx?sslmode=disable"
```

You will expect to open a psql terminal interface to query your local DB if successful. If you prefer accessing with pgAdmin, follow below steps:
1. In the top toolbar, Click **Object** -> **Register** -> **Server**
2. Under *General* tab, type `Olmo-api` in the "Name" field. Choose whatever "Server group" you'd like to put under.
3. Under *Connection* tab, type `localhost` for "Host name/address", `5555` for "Port". You can use default username `postgres` to connect, or username `app` with password `llmz`.
4. Click "Save" button, pgAdmin should be able to load data from your local DB!

### Production

The API uses a [Google Cloud SQL database](https://console.cloud.google.com/sql/instances/llmx-api/users?project=ai2-reviz)
for persistence. To connect to the production database [install and configure the `gcloud` command](https://cloud.google.com/sdk) and run:

```bash
gcloud beta sql connect llmx-api --project ai2-reviz
```

The password for the `postgres` user can be found in 1Password.

If you can't connect to the database or don't have access to the 1Password vault, send a note to
[reops@allenai.org](mailto:reops@allenai.org).


## Schema Migrations

For simplicity this application lacks automated database migrations. Instead the schema is expressed in a single file and migrations are manually executed by piping the content from stdin to the psql command.

### Testing migration on Local

If you change `schema.sql` and you wanna make your local DB that runs on old schema pick up new changes while it's running, besides restarting the DB, you can execute below command:
```bash
docker compose exec -T db psql --user=postgres llmx < schema/schema.sql
```

This pipes the content of `schema.sql` on your host to your local DB running in docker. 

> [!NOTE]
> If there are any changes like adding columns, dropping columns, or updating table constraints, please append at the end of `schema.sql` instead of modifying table attributes directly.


### Running migration on Production

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

