# Migrations
This uses Alembic to auto-generate migrations. The tutorial can be found here: https://alembic.sqlalchemy.org/en/latest/tutorial.html

## Commands
To auto-generate migrations locally:
FLASK_CONFIG_PATH="config.json" MIGRATION_USERNAME=postgres MIGRATION_PASSWORD=llmz alembic revision -m "<YOUR MESSAGE HERE>" --autogenerate

To run migrations locally:
FLASK_CONFIG_PATH="config.json" MIGRATION_USERNAME=postgres MIGRATION_PASSWORD=llmz alembic upgrade head

To downgrade to the original config:
FLASK_CONFIG_PATH="config.json" MIGRATION_USERNAME=postgres MIGRATION_PASSWORD=llmz alembic downgrade base


## Gotchas
If you make a new table you'll need to grant access to it in a second migration. See [this `model_config` migration](./versions/4d6e17a0fdf6_grant_access_to_model_config_table.py) for an example.