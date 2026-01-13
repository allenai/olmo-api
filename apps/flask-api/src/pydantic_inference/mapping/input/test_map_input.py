from pydantic_ai import AudioUrl, DocumentUrl, ImageUrl, VideoUrl
from pydantic_ai.messages import ModelRequest

from db.models.inference_opts import InferenceOpts
from db.models.message import Message
from src.dao.message.message_models import Role
from src.pydantic_inference.mapping.input.map_input import pydantic_map_messages

TEST_VIDEO_URL = "http://localhost:8080/video.mp4"
TEST_IMAGE_URL = "http://localhost:8080/image.JPEG"
TEST_JPG_URL = "http://localhost:8080/image.jpg"
TEST_HTML_URL = "http://localhost:8080/document.html"
TEST_AUDIO_URL = "http://localhost:8080/audio.mp3"
TEST_DOCUMENT_URL = "http://localhost:8080/document.docx"


def test_map_message_with_multimedia_urls() -> None:
    message_id = "user-message-with-multimedia"
    message_content = "test message with multimedia"

    messages = [
        Message(
            id=message_id,
            content=message_content,
            creator="test-user",
            role=Role.User,
            opts=InferenceOpts(),
            root=message_id,
            model_id="test-model",
            model_host="test-backend",
            parent=None,
            model_type="chat",
            expiration_time=None,
            file_urls=[
                TEST_VIDEO_URL,
                TEST_IMAGE_URL,
                TEST_DOCUMENT_URL,
                TEST_AUDIO_URL,
                TEST_JPG_URL,
                TEST_DOCUMENT_URL,
            ],
        )
    ]

    result = pydantic_map_messages(messages=messages, blob_map=None)

    request = next(part for part in result if isinstance(part, ModelRequest))
    user_prompt_parts = request.parts[0].content

    assert user_prompt_parts == [
        message_content,
        VideoUrl(TEST_VIDEO_URL),
        ImageUrl(TEST_IMAGE_URL),
        DocumentUrl(TEST_DOCUMENT_URL),
        AudioUrl(TEST_AUDIO_URL),
        ImageUrl(TEST_JPG_URL),
        DocumentUrl(TEST_DOCUMENT_URL),
    ]
