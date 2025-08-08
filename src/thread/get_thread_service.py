from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src.dao.engine_models.message import Message
from src.thread.thread_models import Thread


def get_thread(thread_id: str, session_maker: sessionmaker[Session]) -> Thread:
    with session_maker.begin() as session:
        message = session.get(Message, thread_id)

        if message is None:
            raise exceptions.NotFound

        return Thread.from_message(message)
