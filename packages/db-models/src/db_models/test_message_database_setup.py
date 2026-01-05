from playground_core.object_id import NewID
from sqlalchemy.orm import Session

from src.dao.message.message_models import Role

from .message import Message
from .model_config import ModelHost
from .tool_definitions import ToolDefinition, ToolSource


def test_tool_def_does_not_delete_when_related_message_does(sql_alchemy: Session):
    message_id = NewID("msg")
    message = Message(
        id=message_id,
        content="test message",
        creator="me",
        role=Role.Assistant,
        root=message_id,
        opts={},
        final=True,
        private=False,
        model_id="test-model",
        model_host=ModelHost.TestBackend.value,
        parent=None,
        expiration_time=None,
    )

    sql_alchemy.add(message)

    tool_definition = ToolDefinition(
        name="test-tool", description="tool for testing", parameters=None, tool_source=ToolSource.INTERNAL
    )

    sql_alchemy.add(tool_definition)

    message.tool_definitions = [tool_definition]

    sql_alchemy.commit()

    loaded_message = sql_alchemy.get(Message, message.id)
    assert loaded_message is not None
    assert loaded_message.tool_definitions is not None
    assert len(loaded_message.tool_definitions) == 1

    loaded_tool_definition = sql_alchemy.get(ToolDefinition, tool_definition.id)
    assert loaded_tool_definition is not None
    assert loaded_tool_definition.messages is not None
    assert len(loaded_tool_definition.messages) == 1

    sql_alchemy.delete(loaded_message)
    sql_alchemy.commit()

    loaded_message_after_deletion = sql_alchemy.get(Message, message.id)
    assert loaded_message_after_deletion is None

    sql_alchemy.refresh(loaded_tool_definition)
    assert loaded_tool_definition is not None
    assert loaded_tool_definition.messages is None or len(loaded_tool_definition.messages) == 0
