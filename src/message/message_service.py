from datetime import UTC, datetime, timedelta

from werkzeug import exceptions

from src import db
from src.auth.auth_service import authn
from src.message.GoogleCloudStorage import GoogleCloudStorage


def get_message(id: str, dbc: db.Client):
    agent = authn()
    message = dbc.message.get(id, agent=agent.client)

    if message is None:
        raise exceptions.NotFound

    if message.creator != agent.client and message.private:
        msg = "You do not have access to that private message."
        raise exceptions.Forbidden(msg)

    return message


def delete_message(id: str, dbc: db.Client, storage_client: GoogleCloudStorage):
    agent = authn()

    message_list = dbc.message.get_by_root(id)
    root_message = next((m for m in message_list if m.id == id), None)

    if root_message is None:
        raise exceptions.NotFound

    if root_message.creator != agent.client:
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

    # Remove messages
    msg_ids = [m.id for m in message_list]
    dbc.message.remove(msg_ids)

    # Remove related rows in Completion table
    related_cpl_ids = [id for id in [m.completion for m in message_list] if id is not None]
    dbc.completion.remove(related_cpl_ids)
