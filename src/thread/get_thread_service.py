from werkzeug import exceptions

from src import db
from src.config.get_config import get_config
from src.dao.message.message_repository import BaseMessageRepository
from src.message.message_service import get_message
from src.thread.thread_models import Thread


def get_thread(thread_id: str, user_id: str, message_repository: BaseMessageRepository, dbc: db.Client) -> Thread:
    config = get_config()
    if config.feature_flags.enable_sqlalchemy_messages:
        messages = message_repository.get(thread_id, user_id)

        if messages is None:
            raise exceptions.NotFound

        return Thread.from_messages(messages)

    thread = get_message(thread_id, dbc)
    if thread is None:
        raise exceptions.NotFound

    return Thread.from_message(thread)
