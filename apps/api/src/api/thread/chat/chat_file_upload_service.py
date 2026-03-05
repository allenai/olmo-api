import asyncio
import os
from collections.abc import Awaitable, Sequence
from typing import Annotated

from fastapi import BackgroundTasks, Depends, UploadFile
from opentelemetry import trace

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.config import settings
from api.gcs_dependency import GoogleCloudStorageDependency
from core.google_cloud_storage import UploadResponse
from core.object_id import ID

tracer = trace.get_tracer(__name__)


class ChatFileUploadService:
    def __init__(
        self,
        background_tasks: BackgroundTasks,
        message_repository: AsyncMessageRepositoryDependency,
        storage: GoogleCloudStorageDependency,
    ):
        self._background_tasks = background_tasks
        self._message_repository = message_repository
        self._storage = storage

    @tracer.start_as_current_span(name="ChatFileUploadService/_update_message_when_files_finish_upload")
    async def _update_message_when_files_finish_upload(
        self, message_id: ID, upload_tasks: Sequence[Awaitable[UploadResponse]]
    ):
        upload_results = await asyncio.gather(*upload_tasks)
        file_urls = [upload_result.public_url for upload_result in upload_results]
        await self._message_repository.set_file_urls_on_message(message_id, file_urls)

    def upload_request_files(self, message_id: ID, root_message_id: ID, files: Sequence[UploadFile]):
        """
        Starts the upload for files and sets a callback to update the message with the file URLs
        """
        tasks: list[Awaitable[UploadResponse]] = []
        for i, file in enumerate(files or []):
            file_extension = os.path.splitext(file.filename)[1] if file.filename is not None else ""
            filename = f"{root_message_id}/{message_id}-{i}{file_extension}"

            upload_response = self._storage.upload_content(
                filename=filename, file_data=file.file, bucket_name=settings.USER_CONTENT_BUCKET, make_file_public=True
            )
            tasks.append(upload_response)

        # This lets us "fire and forget" the work to update the messages when the files finish
        self._background_tasks.add_task(
            self._update_message_when_files_finish_upload, message_id=message_id, upload_tasks=tasks
        )


ChatFileUploadServiceDependency = Annotated[ChatFileUploadService, Depends()]
