import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pydantic_ai.models import Model, StreamedResponse
from pydantic_ai.models.test import TestModel


class SleepTestModel(TestModel):
    @asynccontextmanager
    async def request_stream(self, *args: object, **kwargs: object) -> AsyncIterator[StreamedResponse]:
        await asyncio.sleep(1)
        async with super().request_stream(*args, **kwargs) as stream:  # type: ignore[arg-type]
            yield stream

def get_test_model() -> Model:
    return SleepTestModel()
