from src.dao.message.message_models import Role

from .create_message_request import CreateMessageRequest


def test_message_newline_process():
    msg = "hello \r\n hello \n hi \r\n hello"

    msg_expected = "hello \n hello \n hi \n hello"

    request = CreateMessageRequest(parent=None, content=msg, role=Role.User, model="test", host="test")

    assert request.content == msg_expected
