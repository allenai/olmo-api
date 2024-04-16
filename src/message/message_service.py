from werkzeug import exceptions

from src import db
from src.auth.auth_service import authn


def get_message(id: str, dbc: db.Client):
    agent = authn(dbc)
    message = dbc.message.get(id, agent=agent.client)

    if message is None:
        raise exceptions.NotFound()

    if message.creator != agent.client and message.private:
        raise exceptions.Forbidden("You do not have access to that private message.")

    return message


def delete_message(id: str, dbc: db.Client):
    message_list = dbc.message.get_by_root(id)
    if message_list is None:
        raise exceptions.NotFound()

    # Remove messages
    msg_ids = list(map(lambda m: m.id, message_list))
    dbc.message.remove(msg_ids)

    # Remove related rows in Completion table
    related_cpl_ids = [id for id in list(map(lambda m: m.completion, message_list)) if id is not None]
    dbc.completion.remove(related_cpl_ids)
