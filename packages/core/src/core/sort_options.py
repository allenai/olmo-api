from enum import StrEnum

from pydantic import Field

from core import APIInterface


class SortDirection(StrEnum):
    ASC = "ASC"
    DESC = "DESC"


class SortOptions(APIInterface):
    offset: int | None = Field(default=0, ge=0)
    # TODO: Implement a customizable max_limit if we use this everywhere
    limit: int = Field(default=10, ge=0, le=100)
    field: str | None = Field(default=None, validation_alias="sort")
    order: SortDirection = Field(default=SortDirection.DESC)
