from typing import TYPE_CHECKING, Any, final, override

from pydantic import TypeAdapter
from sqlalchemy import JSON, Dialect, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from sqlalchemy.types import TypeEngine


# Taken from https://gist.github.com/pdmtt/a6dc62f051c5597a8cdeeb8271c1e079?permalink_comment_id=5761533#gistcomment-5761533
@final
class PydanticType(TypeDecorator[Any]):
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

    def __init__(self, pydantic_type: Any) -> None:
        super().__init__()
        self.pydantic_type = pydantic_type
        self._adapter: TypeAdapter[Any] = TypeAdapter(pydantic_type)

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
        value: Any | None,
        dialect: Dialect,
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        return self._adapter.dump_python(value, mode="json")

    @override
    def process_result_value(
        self,
        value: dict[str, Any] | None,
        dialect: Dialect,
    ) -> Any | None:
        return self._adapter.validate_python(value) if value else None

    def __repr__(self) -> str:
        # Used by alembic
        return f"PydanticType({self.pydantic_type.__name__})"
