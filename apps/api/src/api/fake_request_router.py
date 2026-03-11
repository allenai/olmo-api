import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

fake_request_router = APIRouter(prefix="/fake-request")

async def generate_chunks(num: int, delay: float) -> AsyncGenerator[str, None]:
    for i in range(num):
        await asyncio.sleep(delay / 1000)
        yield json.dumps({"chunk": i}) + "\n"

@fake_request_router.get("")
async def fake_response(num: int = Query(default=10), delay: float = Query(default=100.0)) -> StreamingResponse:
    return StreamingResponse(generate_chunks(num=num, delay=delay), media_type="application/jsonl")
