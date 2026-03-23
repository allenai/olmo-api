import asyncio
import os
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, UploadFile
from opentelemetry import trace

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.config import settings
from api.gcs_dependency import GoogleCloudStorageDependency
from core.object_id import ID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core.google_cloud_storage import UploadResponse

tracer = trace.get_tracer(__name__)


class ChatFileUploadService:
    def __init__(
        self,
        message_repository: AsyncMessageRepositoryDependency,
        storage: GoogleCloudStorageDependency,
    ):
        self._message_repository = message_repository
        self._storage = storage

    @tracer.start_as_current_span(name="ChatFileUploadService/upload_request_files")
    async def upload_request_files(self, message_id: ID, root_message_id: ID, files: Sequence[UploadFile]) -> list[str]:
        tasks: list[asyncio.Task[UploadResponse]] = []
        async with asyncio.TaskGroup() as tg:
            for i, file in enumerate(files or []):
                file_extension = os.path.splitext(file.filename)[1] if file.filename is not None else ""
                filename = f"{root_message_id}/{message_id}-{i}{file_extension}"

                task = tg.create_task(
                    self._storage.upload_content(
                        filename=filename,
                        file_data=await file.read(),
                        bucket_name=settings.USER_CONTENT_BUCKET,
                        make_file_public=True,
                    )
                )
                tasks.append(task)

        file_urls = [task.result().public_url for task in tasks]
        return file_urls


ChatFileUploadServiceDependency = Annotated[ChatFileUploadService, Depends()]
