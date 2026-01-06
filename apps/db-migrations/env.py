import os
from logging.config import fileConfig

import alembic_postgresql_enum
from alembic import context
from db.make_url import make_url
from db.models.base import Base
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# If we want to add more schemas we can see if this helps auto-generate them:
# https://stackoverflow.com/a/70571077

env_file = find_dotenv("../.env.test")
load_dotenv(env_file)


conninfo = os.getenv("MIGRATION_CONNINFO")
db_username = os.getenv("MIGRATION_USERNAME")
db_password = os.getenv("MIGRATION_PASSWORD")
db_url = (
    # For some reason "autosave" works in the main application but not in alembic
    make_url(conninfo)
    .set(username=db_username, password=db_password)
    .difference_update_query(["autosave"])
)


def include_enum_name(name: str) -> bool:
    return name not in {"token_type", "model_type"}


alembic_postgresql_enum.set_configuration(
    alembic_postgresql_enum.Config(include_name=include_enum_name, add_type_ignore=True)
)


def include_name(name, type_, parent_names):  # noqa: ARG001
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        include_name=include_name,
        literal_binds=True,
        include_schemas=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        {"sqlalchemy.url": db_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
