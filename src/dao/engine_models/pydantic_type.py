from typing import Any, final

from pydantic import BaseModel
from sqlalchemy import JSON, Dialect, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeEngine
from typing_extensions import override


# Taken from https://gist.github.com/pdmtt/a6dc62f051c5597a8cdeeb8271c1e079?permalink_comment_id=5761533#gistcomment-5761533
@final
class PydanticType(TypeDecorator[BaseModel]):
    """Pydantic type.

    SAVING:
    - Uses SQLAlchemy JSON type under the hood.
    - Acceps the pydantic model and converts it to a dict on save.
    - SQLAlchemy engine JSON-encodes the dict to a string.
    RETRIEVING:
    - Pulls the string from the database.
    - SQLAlchemy engine JSON-decodes the string to a dict.
    - Uses the dict to create a pydantic model.
    """

    # If you intend to use this class with one dialect only,
    # you could pick a type from the specific dialect for
    # simplicity sake.
    #
    # E.g., if you work with PostgreSQL, you can consider using
    # sqlalchemy.dialects.postgresql.JSONB instead of a
    # generic JSON
    # Ref: https://www.postgresql.org/docs/13/datatype-json.html
    #
    # Otherwise, you should implement the `load_dialect_impl`
    # method to handle different dialects. In this case, the
    # impl variable can reference TypeEngine as a placeholder.
    impl = JSONB
    cache_ok = True

    def __init__(self, pydantic_type: type[BaseModel]) -> None:
        super().__init__()
        self.pydantic_type = pydantic_type

    @override
    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[JSONB | JSON]:
        # You should implement this method to handle different dialects
        # if you intend to use this class with more than one.
        # E.g., use JSONB for PostgreSQL and the generic JSON type for
        # other databases.
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

    @override
    def process_bind_param(
        self,
        value: BaseModel | None,
        dialect: Dialect,
    ) -> dict[str, Any] | None:
        if value is None:
            return None

        if not isinstance(value, BaseModel):  # dynamic typing.
            msg = f'The value "{value!r}" is not a pydantic model'
            raise TypeError(msg)

        # Setting mode to "json" entails that you won't need to define a custom json
        # serializer ahead.
        return value.model_dump(mode="json")

    @override
    def process_result_value(
        self,
        value: dict[str, Any] | None,
        dialect: Dialect,
    ) -> BaseModel | None:
        # We're assuming that the value will be a dictionary here.
        validate_on_load = True
        if validate_on_load:
            return self.pydantic_type.model_validate(value) if value else None
        return self.pydantic_type.model_construct(**value) if value else None

    def __repr__(self) -> str:
        # Used by alembic
        return f"PydanticType({self.pydantic_type.__name__})"
