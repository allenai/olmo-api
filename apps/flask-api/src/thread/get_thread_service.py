from werkzeug import exceptions

from core import object_id as obj
from src.dao.message.message_repository import BaseMessageRepository
from src.thread.thread_models import Thread


def get_thread(thread_id: obj.ID, user_id: str, message_repository: BaseMessageRepository) -> Thread:
    messages = message_repository.get_message_with_children(thread_id, user_id)

    if messages is None:
        raise exceptions.NotFound

    return Thread.from_messages(messages)
