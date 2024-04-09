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
    agent = authn(dbc)
    message = dbc.message.get(id)

    if message is None:
        raise exceptions.NotFound()

    if message.creator != agent.client:
        raise exceptions.Forbidden()

    deleted_message = dbc.message.delete(id, agent=agent.client)
    if deleted_message is None:
        raise exceptions.NotFound()

    return deleted_message
