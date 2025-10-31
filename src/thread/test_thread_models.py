from datetime import UTC, datetime

from src.dao.engine_models.tool_definitions import ToolSource
from src.dao.message.message_models import Role
from src.thread.thread_models import FlatMessage, InferenceOptionsResponse, ToolCall

LOREM_IPSUM_160_WORDS = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla tincidunt varius nulla, ut dignissim magna dictum vel. Phasellus finibus eros eget turpis ultricies consequat. Morbi sed ligula in nibh efficitur tempor vel sit amet lorem. Vestibulum facilisis aliquet tempus. Maecenas vitae justo at mi venenatis facilisis. Donec posuere, risus ac viverra commodo, massa dui facilisis tortor, quis sodales magna mauris vel eros. Duis ac ligula vehicula, gravida dolor quis, aliquam orci. Sed leo tortor, vulputate at convallis et, ultrices quis justo. Interdum et malesuada fames ac ante ipsum primis in faucibus. Etiam ac massa eros. Morbi id neque sed risus sagittis maximus. Duis tincidunt laoreet risus eget rutrum. Maecenas sit amet leo odio. Fusce ac quam eget quam porttitor aliquet.

Maecenas eget ex maximus, commodo turpis non, commodo ante. Duis vehicula, nulla quis fringilla blandit, elit est scelerisque dui, nec porta lorem arcu in lacus. Donec semper sed metus at aliquet. Sed iaculis auctor turpis, eu consectetur metus imperdiet eget.
"""


LOREM_IPSUM_150_WORDS = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla tincidunt varius nulla, ut dignissim magna dictum vel. Phasellus finibus eros eget turpis ultricies consequat. Morbi sed ligula in nibh efficitur tempor vel sit amet lorem. Vestibulum facilisis aliquet tempus. Maecenas vitae justo at mi venenatis facilisis. Donec posuere, risus ac viverra commodo, massa dui facilisis tortor, quis sodales magna mauris vel eros. Duis ac ligula vehicula, gravida dolor quis, aliquam orci. Sed leo tortor, vulputate at convallis et, ultrices quis justo. Interdum et malesuada fames ac ante ipsum primis in faucibus. Etiam ac massa eros. Morbi id neque sed risus sagittis maximus. Duis tincidunt laoreet risus eget rutrum. Maecenas sit amet leo odio. Fusce ac quam eget quam porttitor aliquet.

Maecenas eget ex maximus, commodo turpis non, commodo ante. Duis vehicula, nulla quis fringilla blandit, elit est scelerisque dui, nec porta lorem arcu in lacus. Donec semper sed metus at"""


def test_truncates_content_if_required():
    message = FlatMessage(
        id="message",
        content=LOREM_IPSUM_160_WORDS,
        role=Role.ToolResponse,
        opts=InferenceOptionsResponse(),
        root="message",
        created=datetime.now(UTC),
        model_id="test-model",
        model_host="test_backend",
        creator="test-user",
        tool_calls=[
            ToolCall(
                tool_name="tulu-deep-research_serper_google_webpage_search",
                args={},
                tool_call_id="tool_call_1",
                tool_source=ToolSource.MCP,
            )
        ],
    )

    serialized_message = message.model_dump()

    assert serialized_message.get("content") == LOREM_IPSUM_150_WORDS + "…"


def test_keeps_content_if_tool_call_name_does_not_match():
    message = FlatMessage(
        id="message",
        content=LOREM_IPSUM_160_WORDS,
        role=Role.ToolResponse,
        opts=InferenceOptionsResponse(),
        root="message",
        created=datetime.now(UTC),
        model_id="test-model",
        model_host="test_backend",
        creator="test-user",
        tool_calls=[
            ToolCall(tool_name="good_tool_call", args={}, tool_call_id="tool_call_1", tool_source=ToolSource.MCP)
        ],
    )

    serialized_message = message.model_dump()

    assert serialized_message.get("content") == LOREM_IPSUM_160_WORDS
