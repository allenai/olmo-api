import pytest
from sqlalchemy import select

from core import object_id as obj
from core.message.role import Role
from core.object_id import new_id_generator
from db.models import ModelConfig
from db.models.message.message import Message
from e2e.conftest import AuthenticatedClient

msg_id_generator = new_id_generator("msg")

def create_test_message(**msg_fields) -> Message:
   new_id = msg_id_generator()
   msg = {
      "id": msg_fields.get("id", new_id),
      "root": msg_fields.get("root", new_id),
      **msg_fields,
   }
   return Message(**msg)

async def create_test_thread(db_session, user: AuthenticatedClient) -> obj.ID:
   async with db_session() as session, session.begin():
      model_result = await session.scalars(select(ModelConfig).limit(1))
      model = model_result.first()
      if model is None:
         pytest.fail("No models available to test with")

      root_msg = create_test_message(
         content="[Test] root message",
         creator=user.client,
         role=Role.User.value,
         opts={},
         parent=None,
         model_id=model.id,
         model_host=model.host.value,
         final=True,
         expiration_time=None,
      )
      session.add(root_msg)

      msg1 = create_test_message(
         content="[Test] assistant message",
         creator=user.client,
         role=Role.Assistant.value,
         opts={},
         root=root_msg.id,
         parent=root_msg.id,
         model_id=model.id,
         model_host=model.host.value,
         final=True,
         expiration_time=None,
      )
      session.add(msg1)

      msg2 = create_test_message(
         content="[Test] user message",
         creator=user.client,
         role=Role.User.value,
         opts={},
         root=root_msg.id,
         parent=msg1.id,
         model_id=model.id,
         model_host=model.host.value,
         final=True,
         expiration_time=None,
      )
      session.add(msg2)

   return root_msg.id
