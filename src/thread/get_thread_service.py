from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src import db
from src.config.get_config import get_config
from src.dao.engine_models.message import Message
from src.message.message_service import get_message
from src.thread.thread_models import Thread


def get_thread(thread_id: str, session_maker: sessionmaker[Session], dbc: db.Client) -> Thread:
    config = get_config()
    if config.feature_flags.enable_sqlalchemy_messages:
        with session_maker.begin() as session:
            message = session.get(Message, thread_id)

            if message is None:
                raise exceptions.NotFound

            return Thread.from_message(message)

    else:
        thread = get_message(thread_id, dbc)
        if thread is None:
            raise exceptions.NotFound

        return Thread.from_message(thread)
