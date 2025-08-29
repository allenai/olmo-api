import dataclasses
import os
from collections.abc import Callable, Generator
from dataclasses import asdict
from time import time_ns
from typing import Any, cast

from pydantic_ai.direct import model_request_stream_sync
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models import ModelRequestParameters

from src import db, parse
from src.auth.token import Token
from src.config.get_config import cfg
from src.dao.completion import CompletionOutput
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolSource
from src.dao.message.message_models import MessageChunk, MessageStreamError, Role, TokenLogProbs
from src.dao.message.message_repository import BaseMessageRepository
from src.inference.inference_service import get_engine
from src.inference.InferenceEngine import (
    FinishReason,
    InferenceEngineChunk,
    InferenceEngineMessage,
)
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)
from src.message.create_message_service.files import FileUploadResult, upload_request_files
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.inference_logging import log_inference_timing
from src.message.message_chunk import Chunk, StreamEndChunk, StreamStartChunk
from src.message.SafetyChecker import (
    SafetyCheckerType,
)
from src.message.stream_message import StreamMetrics, stream_message_chunks
from src.pydantic_inference.pydantic_ai_helpers import (
    map_pydantic_tool_to_db_tool,
    pydantic_map_chunk,
    pydantic_map_messages,
    pydantic_settings_map,
)
from src.pydantic_inference.pydantic_model_service import get_pydantic_model
from src.util.generator_with_return_value import GeneratorWithReturnValue

from .database import (
    create_assistant_message,
    create_tool_response_message,
    create_user_message,
    setup_msg_thread,
)
from .tools.tool_calls import call_tool, get_pydantic_tool_defs

MAX_REPEATED_TOOL_CALLS = 10


@dataclasses.dataclass
class ParsedMessage:
    content: parse.MessageContent
    role: Role


def create_new_message(
    request: CreateMessageRequestWithFullMessages,
    dbc: db.Client,
    storage_client: GoogleCloudStorage,
    model: ModelConfig,
    safety_check_elapsed_time: float,
    start_time_ns: int,
    agent: Token,
    message_repository: BaseMessageRepository,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
    *,
    is_message_harmful: bool | None = None,
) -> Message | Generator[Message | MessageChunk | MessageStreamError | Chunk]:
    message_chain = setup_msg_thread(
        message_repository,
        model=model,
        request=request,
        agent=agent,
        is_msg_harmful=is_message_harmful,
    )

    if request.role == Role.Assistant:
        if request.parent is None:
            error_message = "parent is required for creating assistant message"
            raise ValueError(error_message)

        assistant_message = create_assistant_message(
            message_repository,
            request.content,
            request.parent,
            model,
            agent,
        )
        assistant_message.final = True
        message_repository.update(assistant_message)

        return assistant_message

    if request.role == Role.User:
        user_message = create_user_message(
            message_repository,
            parent=message_chain[-1] if len(message_chain) > 0 else None,
            request=request,
            agent=agent,
            model=model,
            is_msg_harmful=is_message_harmful,
        )
        message_chain.append(user_message)

        file_uploads = upload_request_files(
            files=request.files,
            message_id=user_message.id,
            storage_client=storage_client,
            root_message_id=message_chain[0].id,
            is_anonymous=agent.is_anonymous_user,
        )
        file_urls = [file.file_url for file in file_uploads or []]
        user_message.file_urls = file_urls

        blob_map: dict[str, FileUploadResult] = {}
        for file in file_uploads:
            blob_map[file.file_url] = file

        return stream_new_message(
            request,
            dbc,
            model,
            safety_check_elapsed_time,
            start_time_ns,
            agent,
            message_repository,
            message_chain,
            user_message,
            checker_type,
            blob_map,
        )

    if request.role == Role.ToolResponse:
        last_assistant_message = find_last_matching(message_chain, lambda m: m.role == Role.Assistant)

        if last_assistant_message is None:
            msg = f"Can not create a tool response. Parent {request.parent_id} not found"
            raise RuntimeError(msg)

        if last_assistant_message.tool_calls is None:
            msg = "Can not create a tool response. Parent has no tools"
            raise RuntimeError(msg)

        tool_call_from_assistant = next(
            (tool for tool in last_assistant_message.tool_calls if tool.tool_call_id == request.tool_call_id), None
        )

        if tool_call_from_assistant is None:
            msg = "Could not find tool id in last assistant message"
            raise RuntimeError(msg)

        source_tool: ToolCall = ToolCall(
            tool_call_id=tool_call_from_assistant.tool_call_id,
            tool_name=tool_call_from_assistant.tool_name,
            args=tool_call_from_assistant.args,
            tool_source=tool_call_from_assistant.tool_source,
            message_id="",
        )

        tool_message = create_tool_response_message(
            message_repository,
            parent=message_chain[-1],
            content=request.content,
            source_tool=source_tool,
            creator=agent.client,
        )
        message_chain.append(tool_message)

        return stream_new_message(
            request,
            dbc,
            model,
            safety_check_elapsed_time,
            start_time_ns,
            agent,
            message_repository,
            message_chain,
            tool_message,
            checker_type,
        )
    msg = "Unsupported role"
    raise RuntimeError(msg)


def stream_new_message(
    request: CreateMessageRequestWithFullMessages,
    dbc: db.Client,
    model: ModelConfig,
    safety_check_elapsed_time: float,
    start_time_ns: int,
    agent: Token,
    message_repository: BaseMessageRepository,
    message_chain: list[Message],
    created_message: Message,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
    blob_map: dict[str, FileUploadResult] | None = None,
) -> Generator[Message | MessageChunk | MessageStreamError | Chunk]:
    yield StreamStartChunk(message=message_chain[0].id)

    if has_pending_tool_calls(message_chain):
        # if we have pending tool calls we should not get an assistant message
        yield prepare_yield_message_chain(message_chain, created_message)
        yield from finalize_messages(message_repository, message_chain, created_message)
        yield StreamEndChunk(message=message_chain[0].id)
        return

    # Finalize the messages and yield
    tool_calls_made = 0
    while tool_calls_made < MAX_REPEATED_TOOL_CALLS:
        stream_metrics = StreamMetrics(
            first_chunk_ns=None, input_token_count=None, output_token_count=None, total_generation_ns=None
        )
        parent = message_chain[-1]
        reply = create_assistant_message(
            message_repository,
            content="",
            parent=parent,
            model=model,
            agent=agent,
        )
        message_chain.append(reply)

        yield prepare_yield_message_chain(message_chain, created_message)

        start_message_generation_ns = time_ns()
        yield from stream_assistant_response(
            request,
            dbc,
            message_repository,
            message_chain,
            model,
            agent,
            blob_map,
            created_message,
            reply,
            stream_metrics,
        )

        if reply.tool_calls is not None and len(reply.tool_calls) > 0:
            last_msg = reply
            for tool in reply.tool_calls:
                if tool.tool_source is not ToolSource.USER_DEFINED:
                    tool_response = call_tool(tool)
                    tool_msg = create_tool_response_message(
                        message_repository,
                        content=tool_response.content,
                        parent=last_msg,
                        source_tool=tool,
                        creator=agent.client,
                    )
                    message_chain.append(tool_msg)

        yield from finalize_messages(message_repository, message_chain, created_message)

        log_create_message_stats(
            created_message,
            reply,
            start_time_ns,
            safety_check_elapsed_time,
            model,
            checker_type,
            start_message_generation_ns,
            stream_metrics,
        )

        yield prepare_yield_message_chain(message_chain, created_message)

        if (
            reply.tool_calls is None
            or len(reply.tool_calls) == 0
            or any(tool.tool_source == ToolSource.USER_DEFINED for tool in reply.tool_calls)
        ):
            break

        tool_calls_made += 1

    yield StreamEndChunk(message=message_chain[0].id)


def log_create_message_stats(
    user_message: Message,
    reply: Message,
    start_time_ns: int,
    safety_check_elapsed_time: float,
    model: ModelConfig,
    checker_type: SafetyCheckerType,
    start_message_generation_ns: int,
    stream_metrics: StreamMetrics,
):
    end_all = time_ns()
    if stream_metrics.first_chunk_ns or start_time_ns < 0:
        log_inference_timing(
            event_type="create_message",
            ttft_ns=(stream_metrics.first_chunk_ns or 0 - start_message_generation_ns),
            total_ns=(end_all - start_time_ns),
            ttft_ms_including_checks=(stream_metrics.first_chunk_ns or 0 - start_time_ns) // 1e6,
            safety_ms=safety_check_elapsed_time,
            input_token_count=-1,
            output_token_count=-1,
            model=model.id,
            safety_check_id=checker_type,
            message_id=user_message.id,
            reply_id=reply.id,
        )


def finalize_messages(message_repository: BaseMessageRepository, message_chain: list[Message], user_message: Message):
    if message_chain[0].final is False and message_chain[0].role == Role.System:
        system_msg = message_chain[0]
        system_msg.final = True
        final_system_message = message_repository.update(system_msg)

        if final_system_message is None:
            final_system_message_error = RuntimeError(f"failed to finalize message {system_msg.id}")
            yield MessageStreamError(
                message=system_msg.id,
                error=str(final_system_message_error),
                reason="finalization failure",
            )
            raise final_system_message_error

    if user_message.final is False:
        user_message.final = True
        final_message = message_repository.update(user_message)
        if final_message is None:
            final_message_error = RuntimeError(f"failed to finalize message {user_message.id}")
            yield MessageStreamError(
                message=user_message.id, error=str(final_message_error), reason="finalization failure"
            )
            raise final_message_error


def stream_assistant_response(
    request: CreateMessageRequestWithFullMessages,
    dbc: db.Client,
    message_repository: BaseMessageRepository,
    message_chain: list[Message],
    model: ModelConfig,
    agent: Token,
    blob_map: dict[str, FileUploadResult] | None,
    input_message: Message,
    reply: Message,
    stream_metrics: StreamMetrics,
) -> Generator[MessageChunk | MessageStreamError | Chunk, Any, None]:
    """
    Adds a new assistant message to the conversation, and streams the llm response to the api
    """
    # Capture the SHA and logger, as the current_app context is lost in the generator.
    sha = os.environ.get("SHA") or "DEV"
    start_generation_ns = time_ns()

    tool_parts: list[ToolCall] = []
    # Now yield each chunk as it's returned.
    finish_reason: FinishReason | None = None
    logprobs: list[list[TokenLogProbs]] = []
    # We keep track of each chunk and the timing information per-chunk
    # so that we can manifest a completion at the end. This will go
    # away when InferD stores this I/O.

    if cfg.feature_flags.enable_pydantic_inference:
        pydantic_chunks: list[Chunk] = []
        pydantic_inference_engine = get_pydantic_model(model)

        first_chunk_ns: int | None = None
        pydantic_messages = pydantic_map_messages(message_chain[:-1], blob_map)
        tools = get_pydantic_tool_defs(input_message) if model.can_call_tools else []

        with model_request_stream_sync(
            model=pydantic_inference_engine,
            messages=pydantic_messages,
            model_settings=pydantic_settings_map(request.opts, model),
            model_request_parameters=ModelRequestParameters(function_tools=tools, allow_text_output=True),
        ) as stream:
            for generator_chunk_pydantic in stream:
                if first_chunk_ns is None:
                    first_chunk_ns = time_ns()

                pydantic_chunk = pydantic_map_chunk(generator_chunk_pydantic, message=reply)
                pydantic_chunks.append(pydantic_chunk)
                yield pydantic_chunk

        full_response = stream.get()
        text_part = next((part for part in full_response.parts if part.part_kind == "text"), None)
        thinking_part = next((part for part in full_response.parts if part.part_kind == "thinking"), None)
        tool_parts = [
            map_pydantic_tool_to_db_tool(reply, part) for part in full_response.parts if isinstance(part, ToolCallPart)
        ]

        stream_metrics.first_chunk_ns = first_chunk_ns
        stream_metrics.input_token_count = -1
        stream_metrics.output_token_count = -1
        stream_metrics.total_generation_ns = time_ns() - start_generation_ns

        output = text_part.content if text_part is not None else ""
        thinking = thinking_part.content if thinking_part is not None else ""
        # TODO finish reason https://ai.pydantic.dev/api/messages/#pydantic_ai.messages.ModelResponse.vendor_details should be here but isn't
    else:
        tool_parts = []
        thinking = None
        chunks: list[MessageChunk] = []

        chain: list[InferenceEngineMessage] = [
            InferenceEngineMessage(
                role=message_in_chain.role,
                content=message_in_chain.content,
                # We only want to add the request files to the new message. The rest will have file urls associated with them
                files=request.files
                if input_message is not None and message_in_chain.id == input_message.id
                else message_in_chain.file_urls,
            )
            for message_in_chain in message_chain[:-1]
        ]
        inference_engine = get_engine(model)
        message_chunks_generator = GeneratorWithReturnValue(
            stream_message_chunks(
                reply_id=reply.id,
                model=model,
                messages=chain,
                opts=request.opts,
                inference_engine=inference_engine,
            )
        )

        for generator_chunk in message_chunks_generator:
            if isinstance(generator_chunk, InferenceEngineChunk):
                mapped_chunk = map_chunk(generator_chunk, message_id=reply.id)
                yield mapped_chunk
                finish_reason = generator_chunk.finish_reason
                chunks.append(mapped_chunk)
            else:
                yield generator_chunk

        output, logprobs = create_output_from_chunks(chunks)
        inference_stream_metrics: StreamMetrics = message_chunks_generator.value

        stream_metrics.first_chunk_ns = inference_stream_metrics.first_chunk_ns
        stream_metrics.input_token_count = inference_stream_metrics.input_token_count
        stream_metrics.output_token_count = inference_stream_metrics.output_token_count
        stream_metrics.total_generation_ns = inference_stream_metrics.total_generation_ns

    prompt = create_prompt_from_engine_input(message_chain)

    gen = stream_metrics.total_generation_ns or 0
    gen //= 1000000

    message_completion = None

    if not agent.is_anonymous_user:
        message_completion = dbc.completion.create(
            prompt,
            [CompletionOutput(output, str(finish_reason), logprobs)],
            request.opts,
            model.model_id_on_host,
            sha,
            tokenize_ms=-1,
            generation_ms=gen,
            queue_ms=0,
            input_tokens=stream_metrics.input_token_count or -1,
            output_tokens=stream_metrics.output_token_count or -1,
        )
    new_log_props: list[list[dict]] = []
    for log_prop_set in logprobs:
        new_log_props.append([asdict(log_prop) for log_prop in log_prop_set])

    reply.content = output
    reply.logprobs = new_log_props
    reply.finish_reason = finish_reason
    reply.tool_calls = tool_parts
    reply.final = True
    reply.completion = message_completion.id if message_completion is not None else None
    reply.thinking = thinking or None

    final_reply = message_repository.update(reply)

    if final_reply is None:
        final_reply_error = RuntimeError(f"failed to finalize message {reply.id}")
        yield MessageStreamError(message=reply.id, error=str(final_reply_error), reason="finalization failure")
        raise final_reply_error


def prepare_yield_message_chain(message_chain: list[Message], user_message: Message):
    repair_children(message_chain)
    user_message_index = next((i for i, message in enumerate(message_chain) if message.id == user_message.id), -1)

    if user_message_index == -1:
        error_msg = "failed to find user message in chain"
        raise RuntimeError(error_msg)

    if user_message_index == 1 and message_chain[0].role == "system":
        return message_chain[0]

    return message_chain[user_message_index]


def repair_children(msg_chain: list[Message]):
    for i, msg in enumerate(msg_chain):
        next_msg = msg_chain[i + 1] if i < len(msg_chain) - 1 else None
        msg.children = [next_msg] if next_msg else []


def map_chunk(chunk: InferenceEngineChunk, message_id: str) -> MessageChunk:
    chunk_logprobs = chunk.logprobs if chunk.logprobs is not None else []
    mapped_logprobs = [
        [TokenLogProbs(token_id=lp.token_id, text=lp.text, logprob=lp.logprob) for lp in lp_list]
        for lp_list in chunk_logprobs
    ]

    return MessageChunk(
        message=message_id,
        content=chunk.content,
        logprobs=mapped_logprobs,
    )


def create_prompt_from_engine_input(
    input_list: list[Message],
) -> str:
    return "\n".join([f"<|{m.role}|>\n{m.content}" for m in input_list])


def create_output_from_chunks(chunks: list[MessageChunk]):
    output = ""
    logprobs: list[list[TokenLogProbs]] = []

    for chunk in cast(list[MessageChunk], chunks):
        output += chunk.content
        if chunk.logprobs is not None and len(chunk.logprobs) > 0:
            logprobs.append(*chunk.logprobs)

    return output, logprobs


def has_pending_tool_calls(chain: list[Message]) -> bool:
    # find the last assistant message in the list...
    # find the current tool responses...
    # if we haven't answered them all return true
    last_assistant_message = find_last_matching(chain, lambda m: m.role == Role.Assistant)

    if last_assistant_message is None:
        return False

    tool_responses = list(filter(lambda msg: msg.role == Role.ToolResponse, chain))
    tool_responses_ids = [tool.tool_calls[0].tool_call_id if tool.tool_calls else None for tool in tool_responses]

    return any(
        tool_call.tool_call_id not in tool_responses_ids for tool_call in last_assistant_message.tool_calls or []
    )


def find_last_matching(arr: list[Message], condition: Callable[[Message], bool]):
    for item in reversed(arr):
        if condition(item):
            return item
    return None  # or raise an exception if not found
