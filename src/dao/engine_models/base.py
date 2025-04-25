import datetime
from typing import Optional

from sqlalchemy import DateTime, Dialect, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


# Taken from https://github.com/litestar-org/advanced-alchemy/blob/27f6f7e48aff36f4ee80b50f7e8268790b1acb4d/advanced_alchemy/types/datetime.py
class DateTimeUTC(TypeDecorator[datetime.datetime]):
    """Timezone Aware DateTime.

    Ensure UTC is stored in the database and that TZ aware dates are returned for all dialects.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    @property
    def python_type(self) -> type[datetime.datetime]:
        return datetime.datetime

    def process_bind_param(
        self, value: Optional[datetime.datetime], dialect: Dialect
    ) -> Optional[datetime.datetime]:
        if value is None:
            return value
        if not value.tzinfo:
            msg = "tzinfo is required"
            raise TypeError(msg)
        return value.astimezone(datetime.timezone.utc)

    def process_result_value(
        self, value: Optional[datetime.datetime], dialect: Dialect
    ) -> Optional[datetime.datetime]:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value


class Base(MappedAsDataclass, DeclarativeBase):
    type_annotation_map = {datetime.datetime: DateTimeUTC}
