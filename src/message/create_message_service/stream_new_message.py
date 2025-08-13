import dataclasses
import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from time import time_ns
from typing import Any, cast

from pydantic_ai.direct import model_request_stream_sync
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import OpenAIModelSettings

from src import db, parse
from src.auth.token import Token
from src.config.get_config import cfg
from src.dao import completion, message
from src.dao.engine_models.model_config import ModelConfig
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
from src.message.message_chunk import Chunk
from src.message.SafetyChecker import (
    SafetyCheckerType,
)
from src.message.stream_message import StreamMetrics, stream_message_chunks
from src.pydantic_inference.pydantic_ai_helpers import pydantic_map_chunk, pydantic_map_messages
from src.pydantic_inference.pydantic_model_service import get_pydantic_model
from src.util.generator_with_return_value import GeneratorWithReturnValue

from .database import create_tool_response_message, create_user_message, setup_msg_thread
from .tools.tool_calls import call_tool, get_tools

MAX_REPEATED_TOOL_CALLS = 10


@dataclasses.dataclass
class ParsedMessage:
    content: parse.MessageContent
    role: message.Role


def stream_new_message(
    request: CreateMessageRequestWithFullMessages,
    dbc: db.Client,
    storage_client: GoogleCloudStorage,
    model: ModelConfig,
    safety_check_elapsed_time: float,
    start_time_ns: int,
    agent: Token,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
    *,
    is_message_harmful: bool | None = None,
) -> (
    message.Message | Generator[message.Message | message.MessageChunk | message.MessageStreamError | Chunk, Any, None]
):
    # We currently want anonymous users' messages to expire after 1 days
    message_expiration_time = datetime.now(UTC) + timedelta(days=1) if agent.is_anonymous_user else None

    message_chain = setup_msg_thread(
        dbc=dbc,
        model=model,
        request=request,
        agent=agent,
        message_expiration_time=message_expiration_time,
        is_msg_harmful=is_message_harmful,
    )
    msg = create_user_message(
        dbc=dbc,
        parent=message_chain[-1] if len(message_chain) > 0 else None,
        request=request,
        agent=agent,
        message_expiration_time=message_expiration_time,
        is_msg_harmful=is_message_harmful,
    )
    message_chain.append(msg)

    file_uploads = upload_request_files(
        files=request.files,
        message_id=msg.id,
        storage_client=storage_client,
        root_message_id=message_chain[0].id,
        is_anonymous=agent.is_anonymous_user,
    )
    # TODO: https://github.com/allenai/playground-issues-repo/issues/9: Get this from the DB
    file_urls = [file.file_url for file in file_uploads or []]
    msg.file_urls = file_urls

    blob_map: dict[str, FileUploadResult] = {}
    for file in file_uploads:
        blob_map[file.file_url] = file

    # Finalize the messages and yield
    final_message = dbc.message.finalize(msg.id, file_urls=msg.file_urls)
    if final_message is None:
        final_message_error = RuntimeError(f"failed to finalize message {msg.id}")
        yield message.MessageStreamError(message=msg.id, error=str(final_message_error), reason="finalization failure")
        raise final_message_error

    tool_calls_made = 0
    while tool_calls_made < MAX_REPEATED_TOOL_CALLS:
        assistant_stream, reply, stream_stats = stream_assistant_response(
            request, dbc, message_chain, model, agent, blob_map, message_expiration_time, msg
        )

        yield from assistant_stream

        if reply.tool_calls is not None and len(reply.tool_calls) > 0:
            last_msg = reply
            for tool in reply.tool_calls:
                tool_response = call_tool(tool)
                tool_msg = create_tool_response_message(
                    dbc=dbc, content=tool_response.content, parent_message=last_msg, source_tool=tool
                )
                message_chain.append(tool_msg)

        yield prepare_yield_message_chain(message_chain, msg)

        if reply.tool_calls is None or len(reply.tool_calls) == 0:
            break

        tool_calls_made += 1

    # first_ns = stream_metrics.first_chunk_ns or 0
    # input_token_count = stream_metrics.input_token_count or -1
    # output_token_count = stream_metrics.output_token_count or -1
    # total_generation_ns = stream_metrics.total_generation_ns or 0
    start_message_generation_ns = time_ns()
    first_ns: int = 0

    # TODO turn back on...
    # end_all = time_ns()
    # if first_ns > start_time_ns and msg is not None:
    #     log_inference_timing(
    #         event_type="create_message",
    #         ttft_ns=(first_ns - start_message_generation_ns),
    #         total_ns=(end_all - start_time_ns),
    #         ttft_ms_including_checks=(first_ns - start_time_ns) // 1e6,
    #         safety_ms=safety_check_elapsed_time,
    #         input_token_count=input_token_count,
    #         output_token_count=output_token_count,
    #         model=model.id,
    #         safety_check_id=checker_type,
    #         message_id=msg.id,
    #         reply_id=reply.id,
    #     )

    return None


def repair_children(msg_chain: list[message.Message]):
    for i, msg in enumerate(msg_chain):
        next_msg = msg_chain[i + 1] if i < len(msg_chain) - 1 else None
        msg.children = [next_msg] if next_msg else None


def stream_assistant_response(
    request: CreateMessageRequestWithFullMessages,
    dbc: db.Client,
    message_chain: list[message.Message],
    model: ModelConfig,
    agent: Token,
    blob_map: dict[str, FileUploadResult],
    message_expiration_time: datetime | None,
    msg: message.Message,
) -> tuple[
    Generator[
        message.Message | message.MessageChunk | message.MessageStreamError | Chunk,
        Any,
        None,
    ],
    message.Message,
    StreamMetrics,
]:
    """
    Adds a new assistant message to the conversation, and streams the llm response to the api
    """
    # Capture the SHA and logger, as the current_app context is lost in the generator.
    sha = os.environ.get("SHA") or "DEV"
    # Create a message that will eventually capture the streamed response.
    # TODO: should handle exceptions mid-stream by deleting and/or finalizing the message
    reply = dbc.message.create(
        "",
        agent.client,
        message.Role.Assistant,
        request.opts,
        model_id=request.model,
        model_host=request.host,
        root=message_chain[-1].root,
        parent=message_chain[-1].id,
        final=False,
        private=request.private,
        model_type=model.model_type,
        expiration_time=message_expiration_time,
    )

    message_chain.append(reply)
    stream_metrics: StreamMetrics = StreamMetrics(
        first_chunk_ns=0, input_token_count=-1, output_token_count=-1, total_generation_ns=0
    )

    def stream_generator():
        tool_parts: list[ToolCallPart] = []
        yield prepare_yield_message_chain(message_chain, msg)

        # Now yield each chunk as it's returned.
        finish_reason: FinishReason | None = None

        input_token_count: int = -1
        output_token_count: int = -1
        total_generation_ns: int = 0

        # We keep track of each chunk and the timing information per-chunk
        # so that we can manifest a completion at the end. This will go
        # away when InferD stores this I/O.

        if cfg.feature_flags.enable_pydantic_inference:
            pydantic_chunks: list[Chunk] = []
            pydantic_inference_engine = get_pydantic_model(model)

            pydantic_messages = pydantic_map_messages(message_chain[:-1], blob_map)
            tools = get_tools() if model.can_call_tools else []
            with model_request_stream_sync(
                model=pydantic_inference_engine,
                messages=pydantic_messages,
                model_settings=OpenAIModelSettings(openai_reasoning_effort="low"),
                model_request_parameters=ModelRequestParameters(function_tools=tools, allow_text_output=True),
            ) as stream:
                for chunk in stream:
                    pydantic_chunk = pydantic_map_chunk(chunk, message_id=reply.id)
                    pydantic_chunks.append(pydantic_chunk)
                    yield pydantic_chunk

            full_response = stream.get()
            text_part = next((part for part in full_response.parts if part.part_kind == "text"), None)
            tool_parts = [part for part in full_response.parts if isinstance(part, ToolCallPart)]

            output = text_part.content if text_part is not None else ""
            logprobs = []
            # TODO finish reason https://ai.pydantic.dev/api/messages/#pydantic_ai.messages.ModelResponse.vendor_details should be here but isn't
        else:
            tool_parts = []
            chunks: list[message.MessageChunk] = []

            chain: list[InferenceEngineMessage] = [
                InferenceEngineMessage(
                    role=message_in_chain.role,
                    content=message_in_chain.content,
                    # We only want to add the request files to the new message. The rest will have file urls associated with them
                    files=request.files
                    if msg is not None and message_in_chain.id == msg.id
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

            for chunk in message_chunks_generator:
                if isinstance(chunk, InferenceEngineChunk):
                    mapped_chunk = map_chunk(chunk, message_id=reply.id)
                    yield mapped_chunk
                    finish_reason = chunk.finish_reason
                    chunks.append(mapped_chunk)
                else:
                    yield chunk

            # TODO: Looks like these are not working with Cirrascale
            completed_stream_metrics = message_chunks_generator.value
            stream_metrics.first_chunk_ns = completed_stream_metrics.first_chunk_ns or 0
            stream_metrics.input_token_count = completed_stream_metrics.input_token_count or -1
            stream_metrics.output_token_count = stream_metrics.output_token_count or -1
            stream_metrics.total_generation_ns = stream_metrics.total_generation_ns or 0

            output, logprobs = create_output_from_chunks(chunks)

        gen = total_generation_ns
        gen //= 1000000

        prompt = create_prompt_from_engine_input(message_chain)

        message_completion = None
        if not agent.is_anonymous_user:
            message_completion = dbc.completion.create(
                prompt,
                [completion.CompletionOutput(output, str(finish_reason), logprobs)],
                request.opts,
                model.model_id_on_host,
                sha,
                tokenize_ms=-1,
                generation_ms=gen,
                queue_ms=0,
                input_tokens=input_token_count,
                output_tokens=output_token_count,
            )

        final_reply = dbc.message.finalize(
            reply.id,
            output,
            logprobs,
            message_completion.id if message_completion is not None else None,
            finish_reason,
            tool_calls=tool_parts,
        )

        reply.content = output
        reply.logprobs = logprobs
        reply.finish_reason = finish_reason
        reply.tool_calls = tool_parts
        reply.final = True
        reply.completion = message_completion.id if message_completion is not None else None

        if final_reply is None:
            final_reply_error = RuntimeError(f"failed to finalize message {reply.id}")
            yield message.MessageStreamError(
                message=reply.id, error=str(final_reply_error), reason="finalization failure"
            )
            raise final_reply_error

    return stream_generator(), reply, stream_metrics


def prepare_yield_message_chain(message_chain: list[message.Message], user_message: message.Message):
    user_message_index = next((i for i, message in enumerate(message_chain) if message.id == user_message.id), -1)

    repair_children(message_chain)

    if user_message_index == -1:
        error_msg = "failed to find user message in chain"
        raise RuntimeError(error_msg)

    if user_message_index == 1 and message_chain[0].role == "system":
        return message_chain[0]

    return message_chain[user_message_index]


def map_chunk(chunk: InferenceEngineChunk, message_id: str) -> message.MessageChunk:
    chunk_logprobs = chunk.logprobs if chunk.logprobs is not None else []
    mapped_logprobs = [
        [message.TokenLogProbs(token_id=lp.token_id, text=lp.text, logprob=lp.logprob) for lp in lp_list]
        for lp_list in chunk_logprobs
    ]

    return message.MessageChunk(
        message=message_id,
        content=chunk.content,
        logprobs=mapped_logprobs,
    )


def create_prompt_from_engine_input(
    input_list: list[message.Message],
) -> str:
    return "\n".join([f"<|{m.role}|>\n{m.content}" for m in input_list])


def create_output_from_chunks(chunks: list[message.MessageChunk]):
    output = ""
    logprobs: list[list[message.TokenLogProbs]] = []

    for chunk in cast(list[message.MessageChunk], chunks):
        output += chunk.content
        if chunk.logprobs is not None and len(chunk.logprobs) > 0:
            logprobs.append(*chunk.logprobs)

    return output, logprobs
