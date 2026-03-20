from api.thread.chat.mapping.pydantic_ai_mapping import map_messages_to_pydantic_ai_format
from core.message.role import Role
from db.models.inference_opts import InferenceOpts
from db.models.message import Message


def test_map_message_with_system_prompt() -> None:
    message_id = "user-message-with-system-prompt"
    system_prompt = "system prompt"
    user_message = "user message"

    messages = [
        Message(
            id=message_id,
            content=system_prompt,
            creator="test-user",
            role=Role.System,
            opts=InferenceOpts(),
            root=message_id,
            model_id="test-model",
            model_host="test-backend",
            parent=None,
            model_type="chat",
            expiration_time=None,
        ),
        Message(
            content=user_message,
            creator="test-user",
            role=Role.User,
            opts=InferenceOpts(),
            root=message_id,
            model_id="test-model",
            model_host="test-backend",
            parent=None,
            model_type="chat",
            expiration_time=None,
        ),
    ]

    mapped_messages = map_messages_to_pydantic_ai_format(messages)

    assert len(mapped_messages) == 1

    # There's a bug with Pydantic AI where they give messages a run ID if the run ID is None
    # This causes issues when they're computing what messages in a run are new
    # If there's only one message they'll assume it's part of this run and include it in the new messages
    # To work around that, we give the message a fake run_id
    assert mapped_messages[0].run_id == message_id

    assert len(mapped_messages[0].parts) == 2, "Mapped message did not have one system part and one user part"
    system_prompt_part = mapped_messages[0].parts[0]
    assert system_prompt_part.part_kind == "system-prompt"
    assert system_prompt_part.content == system_prompt

    user_prompt_part = mapped_messages[0].parts[1]
    assert user_prompt_part.part_kind == "user-prompt"
    assert user_prompt_part.content == [user_message]
