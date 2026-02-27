from core import object_id as obj
from core.message.role import Role
from core.object_id import new_id_generator
from db.models.inference_opts import InferenceOpts
from db.models.message.message import Message
from e2e.conftest import AuthenticatedClient, DatabaseSession

msg_id_generator = new_id_generator("msg")


def create_test_message(**msg_fields) -> Message:
    new_id = msg_id_generator()
    msg = {
        "id": msg_fields.get("id", new_id),
        "root": msg_fields.get("root", new_id),
        "model_id": "test-model",
        "model_host": "TestBackend",
        "final": True,
        "parent": None,
        "opts": msg_fields.get("opts", InferenceOpts()),
        "expiration_time": None,
        **msg_fields,
    }
    return Message(**msg)


async def create_test_thread(db_session: DatabaseSession, user: AuthenticatedClient) -> tuple[obj.ID, list[Message]]:
    messages: list[Message] = []
    async with db_session() as session, session.begin():
        root_msg = create_test_message(
            content="[Test] root message",
            creator=user.client,
            role=Role.User.value,
        )
        session.add(root_msg)
        messages.append(root_msg)

        msg1 = create_test_message(
            content="[Test] user message",
            creator=user.client,
            role=Role.User.value,
            root=root_msg.id,
            parent=root_msg.id,
        )
        session.add(msg1)
        messages.append(msg1)

        msg2 = create_test_message(
            content="[Test] assistant message",
            creator=user.client,
            role=Role.Assistant.value,
            root=root_msg.id,
            parent=msg1.id,
        )
        session.add(msg2)

    return root_msg.id, messages
