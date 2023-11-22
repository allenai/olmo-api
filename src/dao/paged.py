from dataclasses import dataclass
from typing import Optional
from flask import Request
from werkzeug import exceptions
from enum import StrEnum

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
    offset: Optional[int] = None
    limit: Optional[int] = None
    sort: Optional[Sort] = None

@dataclass
class List:
    meta: ListMeta

@dataclass
class Opts:
    offset: Optional[int] = None
    limit: Optional[int] = None
    sort: Optional[Sort] = None

def parse_opts_from_querystring(request: Request, max_limit: int = 100) -> Opts:
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError as e:
        raise exceptions.BadRequest(f"invalid offset: {e}")
    if offset < 0:
        raise exceptions.BadRequest("invalid offset: must be >= 0")

    try:
        limit = int(request.args.get("limit", 10))
    except ValueError as e:
        raise exceptions.BadRequest(f"invalid limit: {e}")
    if limit < 0:
        raise exceptions.BadRequest("invalid limit: must be >= 0")
    if limit > max_limit:
        raise exceptions.BadRequest(f"invalid limit: must be <= {max_limit}")

    try:
        field = request.args.get("sort")
        dir = request.args.get("order", None, type=lambda s: s.upper())
        if field is None and dir is not None:
            raise ValueError("order specified without sort")
        if dir is None:
            dir = SortDirection.DESC.value
        sort = Sort(field, SortDirection(dir)) if field is not None else None
    except ValueError as e:
        raise exceptions.BadRequest(f"invalid sort: {e}")

    return Opts(offset, limit, sort)


