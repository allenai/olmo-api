from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy import delete

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.db.sqlalchemy_engine import SessionDependency
from api.service_errors import ForbiddenError, NotFoundError
from core.auth.token import Token
from db.models.completion import Completion


class ThreadDeleteService:
    def __init__(self, session: SessionDependency, message_repository: AsyncMessageRepositoryDependency):
        self.session = session
        self.message_repository = message_repository

    async def delete(self, thread_id: str, user: Token) -> None:
        async with self.session.begin():
            messages = await self.message_repository.get_messages_by_root_for_delete(message_id=thread_id)

            # we _should_ have the root message already
            root_message = next((msg for msg in messages if msg.id == thread_id), None)

            if root_message is None:
                not_found_message = f"Thread with id {thread_id} was not found, unable to delete"
                raise NotFoundError(not_found_message)

            if user.is_anonymous_user:
                anon_forbidden_message = "Anonymous user does not have permission to delete the current thread."
                raise ForbiddenError(anon_forbidden_message)

            if root_message.creator != user.client:
                auth_forbidden_message = "The current thread was not created by the current user. You do not have permission to delete the current thread."
                raise ForbiddenError(auth_forbidden_message)

            # prevent deletion if the current thread is out of the 30-day window
            if datetime.now(UTC) - root_message.created > timedelta(days=30):
                msg = "The current thread is over 30 days."
                raise ForbiddenError(msg)

            # TODO: Fix GCS
            #
            # files_to_delete = [
            #     file_url for message in messages if message.file_urls is not None for file_url in message.file_urls
            # ]
            #
            #
            # storage_client.delete_multiple_files_by_url(
            #     files_to_delete, bucket_name=config.google_cloud_services.storage_bucket
            # )

            message_ids = [msg.id for msg in messages]
            await self.message_repository.delete_many(message_ids)

            # Remove related rows in Completion table
            #
            # no cascade here =/
            related_cpl_ids = [id for id in [m.completion for m in messages] if id is not None]
            await self.session.execute(delete(Completion).where(Completion.id.in_(related_cpl_ids)))


ThreadDeleteServiceDependency = Annotated[ThreadDeleteService, Depends()]
