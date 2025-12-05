import pytest
from pydantic import ValidationError

from src.dao.engine_models.input_parts import Molmo2PointPart
from src.dao.message.message_models import Role

from .create_message_request import CreateMessageRequest


def test_message_newline_process():
    msg = "hello \r\n hello \n hi \r\n hello"

    msg_expected = "hello \n hello \n hi \n hello"

    request = CreateMessageRequest(parent=None, content=msg, role=Role.User, model="test", host="test")

    assert request.content == msg_expected


@pytest.mark.parametrize(
    ("content", "input_parts"),
    [
        pytest.param(None, [Molmo2PointPart(x=0, y=0, time=0.0).model_dump_json()]),
        pytest.param("content message", None),
        pytest.param("content message", [Molmo2PointPart(x=0, y=0, time=0.0).model_dump_json()]),
    ],
)
def test_content_and_input_parts_validation_passes(content: str | None, input_parts: str | None):
    CreateMessageRequest.model_validate({
        "content": content,
        "input_parts": input_parts,
        "model": "test",
        "host": "test",
    })


@pytest.mark.parametrize(
    ("content", "input_parts"),
    [pytest.param(None, []), pytest.param("", []), pytest.param("", None), pytest.param(None, None)],
)
def test_content_and_input_parts_validation_fails(content: str | None, input_parts: str | None):
    with pytest.raises(ValidationError):
        CreateMessageRequest.model_validate({
            "content": content,
            "input_parts": input_parts,
            "model": "test",
            "host": "test",
        })
