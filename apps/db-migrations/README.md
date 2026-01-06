# Migrations
This uses Alembic to auto-generate migrations. The tutorial can be found here: https://alembic.sqlalchemy.org/en/latest/tutorial.html

## Commands
### To auto-generate migrations locally:
`uv run alembic revision -m "<YOUR MESSAGE HERE>" --autogenerate`

### To run migrations locally:
`uv run alembic upgrade head`

### To downgrade to the original config:
`uv run alembic downgrade base`

### To generate migration sql for prod:
`uv run alembic upgrade head --sql > schema/02-schema.sql`

## Gotchas
If you make a new table you'll need to grant access to it in a second migration. See [this `model_config` migration](./versions/4d6e17a0fdf6_grant_access_to_model_config_table.py) for an example.

You'll also need to make sure it's imported into `env.py`. In most cases you can add it to `packages/db/models/__init__.py` and it will automatically import the model.

### Running migration on Production

> [!WARNING]
> If you're executing migrations in production you could break the public API, so tread carefully.

To run schema migrations:

1. Make a new migration file:
    `uv run alembic upgrade head --sql > schema/02-schema.sql`
2. Connect to the database:

    ```
    gcloud beta sql connect llmx-api --project ai2-reviz --port 5555
    ```

   When prompted for a password don't enter one, but leave the program running (it opens a tunnel).

3. Obtain the password for the `postgres` user from 1Password.

4. In a new terminal, run the command below, replacing `$PASSWD` with the value from the previous step.

    ```bash
    psql "postgres://postgres:$PASSWD@localhost:5555/llmx?sslmode=disable" < schema/schema.sql
    ```
    

### Running a single migration on Production

1. Get the SQL:
    `uv run alembic upgrade <previous-revision>:head --sql`

2. Follow the same connection steps as above

3. Wrap the upgrade SQL in a transaction with a lock timeout, then execute it:
    ```sql
    BEGIN;
    SET LOCAL lock_timeout = '30s';
    
    <upgrade SQL here>

    COMMIT;
    ```


### Reverting a migration on Production
If you know which revision caused the problem, run 
```bash
uv run alembic downgrade head:<bad-revision> --sql > downgrade.sql
```

Then run the downgrade SQL on prod.