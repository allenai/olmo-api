from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session
from werkzeug import exceptions

from src import db
from src.auth.token import Token
from src.dao.message.message_repository import MessageRepository, map_sqla_to_old
from src.dependencies import DBSession
from src.message.GoogleCloudStorage import GoogleCloudStorage


def get_message(id: str, token: Token, session: Session):
    message_repository = MessageRepository(session)
    message = message_repository.get_message_by_id(id)

    if message is None:
        raise exceptions.NotFound

    if message is None:
        raise exceptions.NotFound

    if message.creator != token.client and message.private:
        msg = "You do not have access to that private message."
        raise exceptions.Forbidden(msg)

    return map_sqla_to_old(message)


def delete_message(id: str, dbc: db.Client, storage_client: GoogleCloudStorage, token: Token, session: Session):
    message_repository = MessageRepository(session)

    message_list = message_repository.get_messages_by_root_for_delete(id)

    root_message = next((m for m in message_list if m.id == id), None)

    if root_message is None:
        raise exceptions.NotFound

    if root_message.creator != token.client:
        msg = "The current thread was not created by the current user. You do not have permission to delete the current thread."
        raise exceptions.Forbidden(msg)

    # prevent deletion if the current thread is out of the 30-day window
    if datetime.now(UTC) - root_message.created > timedelta(days=30):
        msg = "The current thread is over 30 days."
        raise exceptions.Forbidden(msg)

    files_to_delete = [
        file_url for message in message_list if message.file_urls is not None for file_url in message.file_urls
    ]

    storage_client.delete_multiple_files_by_url(files_to_delete)

    for m in message_list:
        message_repository.delete(m.id)

    # Remove related rows in Completion table
    related_cpl_ids = [id for id in [m.completion for m in message_list] if id is not None]
    dbc.completion.remove(related_cpl_ids)


# Service class with dependency injection
class MessageService:
    """
    Message service with dependency-injected database session.

    This service encapsulates message operations and receives
    its dependencies through constructor injection.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_message(self, id: str, token: Token):
        """Get a message by ID with authorization check"""
        message_repository = MessageRepository(self.session)
        message = message_repository.get_message_by_id(id)

        if message is None:
            raise exceptions.NotFound

        if message.creator != token.client and message.private:
            msg = "You do not have access to that private message."
            raise exceptions.Forbidden(msg)

        return map_sqla_to_old(message)

    def delete_message(self, id: str, dbc: db.Client, storage_client: GoogleCloudStorage, token: Token):
        """Delete a message thread with authorization and time window checks"""
        message_repository = MessageRepository(self.session)

        message_list = message_repository.get_messages_by_root_for_delete(id)

        root_message = next((m for m in message_list if m.id == id), None)

        if root_message is None:
            raise exceptions.NotFound

        if root_message.creator != token.client:
            msg = "The current thread was not created by the current user. You do not have permission to delete the current thread."
            raise exceptions.Forbidden(msg)

        # prevent deletion if the current thread is out of the 30-day window
        if datetime.now(UTC) - root_message.created > timedelta(days=30):
            msg = "The current thread is over 30 days."
            raise exceptions.Forbidden(msg)

        files_to_delete = [
            file_url for message in message_list if message.file_urls is not None for file_url in message.file_urls
        ]

        storage_client.delete_multiple_files_by_url(files_to_delete)

        for m in message_list:
            message_repository.delete(m.id)

        # Remove related rows in Completion table
        related_cpl_ids = [id for id in [m.completion for m in message_list] if id is not None]
        dbc.completion.remove(related_cpl_ids)


def get_message_service(session: DBSession) -> MessageService:
    """Dependency provider for MessageService"""
    return MessageService(session)


# Type alias for dependency injection
MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]
