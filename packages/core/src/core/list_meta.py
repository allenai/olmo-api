from dataclasses import dataclass

from core.sort_options import SortDirection


@dataclass
class Sort:
    field: str
    direction: SortDirection = SortDirection.DESC


@dataclass
class ListMeta:
    total: int
    offset: int | None = None
    limit: int | None = None
    sort: Sort | None = None
