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
    # message = dbc.message.get(id)
    print("deleting message!")
    message_list = dbc.message.get_by_root(id)
    if message_list is None:
        raise exceptions.NotFound()

    print("all message list")
    print(message_list)
    related_cpl_ids = [id for id in list(map(lambda m: m.completion, message_list)) if id is not None]
    print("related_cpl_ids_3")
    print(related_cpl_ids)

    dbc.completion.remove(related_cpl_ids)
    print("delete complete!")
    # if message.creator != agent.client:
    #     raise exceptions.Forbidden()

    # deleted_message = dbc.message.delete(id, agent=agent.client)
    # if deleted_message is None:
    #     raise exceptions.NotFound()

    # return deleted_message
