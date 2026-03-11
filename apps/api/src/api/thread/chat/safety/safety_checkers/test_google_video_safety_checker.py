from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from google.cloud.videointelligence_v1 import (
    AnnotateVideoResponse,
    ExplicitContentAnnotation,
    ExplicitContentFrame,
    Likelihood,
    VideoAnnotationResults,
)
from pytest_mock import MockerFixture

from api.async_message_repository.async_message_repository import AsyncMessageRepository
from api.config import settings
from api.thread.chat.safety.safety_checkers.google_video_safety_checker import (
    GoogleVideoIntelligenceSafetyChecker,
    _handle_video_safety_check_async,
    handle_video_safety_check,
)
from core.google_cloud_storage import GoogleCloudStorage
from db.models.message import Message

from .safety_checker_base import (
    SafetyCheckRequest,
    SkippedSafetyCheckResponse,
)

SAFETY_MODULE = "api.thread.chat.safety.safety_checkers.google_video_safety_checker"

OPERATION_NAME = "projects/test/operations/testing123"
MESSAGE_ID = "msg_testing123"
FILE_URL = "gs://safety-bucket/test.mp4"


def create_annotate_video_response(pornography_likelihood: int) -> AnnotateVideoResponse:
    return AnnotateVideoResponse(
        annotation_results=[
            VideoAnnotationResults(
                explicit_annotation=ExplicitContentAnnotation(
                    frames=[ExplicitContentFrame(pornography_likelihood=pornography_likelihood)]
                )
            )
        ]
    )


def mock_operation(mocker: MockerFixture, response: AnnotateVideoResponse):
    operation = AsyncMock()
    operation.result = AsyncMock(return_value=response)
    mocker.patch(f"{SAFETY_MODULE}.operation_async.from_gapic", return_value=operation)


@pytest.fixture(autouse=True)
def mock_session():
    session = AsyncMock()
    with patch(f"{SAFETY_MODULE}._make_worker_sessionmaker", return_value=MagicMock(return_value=session)):
        yield session


@pytest.fixture(autouse=True)
def mock_video_client():
    client = MagicMock()
    with patch(f"{SAFETY_MODULE}.get_video_intelligence_client_async", return_value=client):
        yield client


@pytest.fixture
def mock_message():
    msg = MagicMock(spec=Message)
    msg.harmful = False
    msg.file_urls = None
    return msg


@pytest.fixture(autouse=True)
def mock_repo(mock_message):
    repo = AsyncMock(spec=AsyncMessageRepository)
    repo.get_message_by_id = AsyncMock(return_value=mock_message)
    with patch(f"{SAFETY_MODULE}.AsyncMessageRepository", return_value=repo):
        yield repo


@pytest.fixture(autouse=True)
def mock_gcs():
    gcs = AsyncMock(spec=GoogleCloudStorage)
    with patch(f"{SAFETY_MODULE}.get_google_cloud_storage", return_value=gcs):
        yield gcs


async def test_deferred_strategy_path(mocker: MockerFixture, mock_video_client):
    # Just this test cares about this code path
    mocker.patch.object(settings, "VIDEO_SAFETY_CHECK_WORKER_STRATEGY", "deferred")

    op = MagicMock()
    op.operation.name = OPERATION_NAME
    mock_video_client.annotate_video = AsyncMock(return_value=op)
    mock_send = mocker.patch.object(handle_video_safety_check, "send")

    result = await GoogleVideoIntelligenceSafetyChecker().check_request(
        SafetyCheckRequest(content=FILE_URL, name="test.mp4", message_id=MESSAGE_ID)
    )

    assert isinstance(result, SkippedSafetyCheckResponse)
    assert result.is_safe()
    mock_send.assert_called_once_with(operation_name=OPERATION_NAME, file_url=FILE_URL, message_id=MESSAGE_ID)


async def test_safe_video(mocker: MockerFixture, mock_video_client, mock_repo, mock_gcs, mock_message):
    mock_video_client.transport.operations_client.get_operation = AsyncMock(return_value=MagicMock())
    mock_operation(mocker, create_annotate_video_response(pornography_likelihood=Likelihood.UNLIKELY))

    await _handle_video_safety_check_async(operation_name=OPERATION_NAME, file_url=FILE_URL, message_id=MESSAGE_ID)

    assert mock_message.harmful is False
    mock_repo.update.assert_awaited_once()
    mock_gcs.delete_file.assert_not_called()


async def test_unsafe_video(mocker: MockerFixture, mock_video_client, mock_repo, mock_gcs, mock_message):
    mock_video_client.transport.operations_client.get_operation = AsyncMock(return_value=MagicMock())
    mock_operation(mocker, create_annotate_video_response(pornography_likelihood=Likelihood.VERY_LIKELY))
    mock_message.file_urls = ["gs://public-bucket/video.mp4"]

    await _handle_video_safety_check_async(operation_name=OPERATION_NAME, file_url=FILE_URL, message_id=MESSAGE_ID)

    assert mock_message.harmful is True
    mock_gcs.delete_file.assert_awaited_once()
    mock_gcs.delete_multiple_files_by_url.assert_awaited_once_with(
        file_urls=["gs://public-bucket/video.mp4"], bucket_name=ANY
    )
    assert mock_message.file_urls is None
    mock_repo.update.assert_awaited_once()


async def test_already_harmful_message_stays_harmful(mocker: MockerFixture, mock_video_client, mock_message):
    mock_video_client.transport.operations_client.get_operation = AsyncMock(return_value=MagicMock())
    mock_operation(mocker, create_annotate_video_response(pornography_likelihood=Likelihood.UNLIKELY))
    mock_message.harmful = True

    await _handle_video_safety_check_async(operation_name=OPERATION_NAME, file_url=FILE_URL, message_id=MESSAGE_ID)

    assert mock_message.harmful is True
