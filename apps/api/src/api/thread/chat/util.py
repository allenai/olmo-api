from collections.abc import Sequence

from db.models.message import Message


def attach_message_children(msg_chain: Sequence[Message]):
    for i, msg in enumerate(msg_chain):
        next_msg = msg_chain[i + 1] if i < len(msg_chain) - 1 else None
        # This will need to change if we allow threading
        if next_msg and not next_msg.children:
            msg.children = [next_msg]
            next_msg.parent = msg.id

    return msg_chain
