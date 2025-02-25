from dataclasses import dataclass
from enum import StrEnum

from flask import Request
from werkzeug import exceptions


class SortDirection(StrEnum):
    ASC = "ASC"
    DESC = "DESC"


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


@dataclass
class List:
    meta: ListMeta


@dataclass
class Opts:
    offset: int | None = None
    limit: int | None = None
    sort: Sort | None = None


def parse_opts_from_querystring(request: Request, max_limit: int = 100) -> Opts:
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError as e:
        msg = f"invalid offset: {e}"
        raise exceptions.BadRequest(msg)
    if offset < 0:
        msg = "invalid offset: must be >= 0"
        raise exceptions.BadRequest(msg)

    try:
        limit = int(request.args.get("limit", 10))
    except ValueError as e:
        msg = f"invalid limit: {e}"
        raise exceptions.BadRequest(msg)
    if limit < 0:
        msg = "invalid limit: must be >= 0"
        raise exceptions.BadRequest(msg)
    if limit > max_limit:
        msg = f"invalid limit: must be <= {max_limit}"
        raise exceptions.BadRequest(msg)

    try:
        field = request.args.get("sort")
        dir = request.args.get("order", None, type=lambda s: s.upper())
        if field is None and dir is not None:
            msg = "order specified without sort"
            raise ValueError(msg)
        if dir is None:
            dir = SortDirection.DESC.value
        sort = Sort(field, SortDirection(dir)) if field is not None else None
    except ValueError as e:
        msg = f"invalid sort: {e}"
        raise exceptions.BadRequest(msg)

    return Opts(offset, limit, sort)
