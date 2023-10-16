from dataclasses import dataclass
from typing import Optional
from flask import Request
from werkzeug import exceptions

@dataclass
class ListMeta:
    total: int
    offset: Optional[int] = None
    limit: Optional[int] = None

@dataclass
class List:
    meta: ListMeta

@dataclass
class Opts:
    offset: Optional[int] = None
    limit: Optional[int] = None

def parse_opts_from_querystring(request: Request) -> Opts:
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
    if limit > 100:
        raise exceptions.BadRequest("invalid limit: must be <= 100")

    return Opts(offset, limit)


