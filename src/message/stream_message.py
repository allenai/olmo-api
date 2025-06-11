import multiprocessing
import multiprocessing.pool
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from functools import reduce
from time import time_ns
from typing import Any

import beaker
import grpc
from flask import current_app

from src.dao.engine_models.model_config import ModelConfig
from src.dao.message import InferenceOpts, MessageStreamError
from src.inference.InferenceEngine import (
    FinishReason,
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
)


@dataclass
class StreamMetrics:
    first_chunk_ns: int | None
    input_token_count: int | None
    output_token_count: int | None
    total_generation_ns: int | None


def stream_message_chunks(
    reply_id: str,
    model: ModelConfig,
    messages: Sequence[InferenceEngineMessage],
    opts: InferenceOpts,
    inference_engine: InferenceEngine,
) -> Generator[InferenceEngineChunk | MessageStreamError, Any, StreamMetrics]:
    logger = current_app.logger

    finish_reason: FinishReason | None = None
    first_chunk_ns: int | None = None
    input_token_count: int | None = None
    output_token_count: int | None = None

    start_generation_ns = time_ns()
    try:
        message_generator = inference_engine.create_streamed_message(
            model=model.model_id_on_host,
            messages=messages,
            inference_options=InferenceOptions(**opts.model_dump()),
        )

        # Adapted from https://anonbadger.wordpress.com/2018/12/15/python-signal-handlers-and-exceptions/
        pool = multiprocessing.pool.ThreadPool(processes=1)
        results = pool.apply_async(lambda: next(message_generator))

        # We handle the first chunk differently since we want to timeout if it takes longer than 30 seconds
        first_chunk = results.get(30.0)

        if first_chunk_ns is None:
            first_chunk_ns = time_ns()

        yield first_chunk

        for chunk in message_generator:
            yield chunk
            input_token_count = chunk.input_token_count
            output_token_count = chunk.output_token_count

    # TODO: Move engine-specific exceptions into the InferenceEngine for that engine
    # For example, this would move to the InferDEngine
    except grpc.RpcError as e:
        finish_reason = FinishReason.BadConnection
        err = f"inference failed: {e}"
        logger.exception(
            "GRPC inference failed",
            extra={
                "message_id": reply_id,
                "model": model.id,
                "host": model.host,
                "finish_reason": finish_reason,
                "event": "inference.stream-error",
            },
        )
        yield MessageStreamError(message=reply_id, error=err, reason="grpc inference failed")

    except beaker.exceptions.BeakerQueueNotFound as e:  # type: ignore
        finish_reason = FinishReason.Unknown
        err = f"inference failed: {e}"
        logger.exception(
            "model queue not found",
            extra={
                "message_id": reply_id,
                "model": model.id,
                "host": model.host,
                "finish_reason": finish_reason,
                "event": "inference.stream-error",
            },
        )
        yield MessageStreamError(message=reply_id, error=err, reason="model queue not found")

    except multiprocessing.TimeoutError:
        finish_reason = FinishReason.ModelOverloaded

    except ValueError as e:
        finish_reason = FinishReason.ValueError
        logger.exception(
            "Value Error from inference",
            extra={
                "message_id": reply_id,
                "model": model.id,
                "host": model.host,
                "finish_reason": finish_reason,
                "event": "inference.stream-error",
            },
        )
        # value error can be like when context length is too long
        yield MessageStreamError(message=reply_id, error=f"{e}", reason="value error from inference result")

    except Exception as e:
        finish_reason = FinishReason.Unknown
        logger.exception(
            "Unexpected error during inference",
            extra={
                "message_id": reply_id,
                "model": model.id,
                "host": model.host,
                "finish_reason": finish_reason,
                "event": "inference.stream-error",
            },
        )
        yield MessageStreamError(message=reply_id, error=f"{e}", reason="general exception")

    match finish_reason:
        case FinishReason.UnclosedStream:
            logger.error(
                "Finished with reason UnclosedStream",
                extra={
                    "message_id": reply_id,
                    "model": model.id,
                    "host": model.host,
                    "finish_reason": finish_reason,
                    "event": "inference.stream-error",
                },
            )
            err = "inference failed for an unknown reason: sometimes this happens when the prompt is too long"
            yield MessageStreamError(message=reply_id, error=err, reason=finish_reason)

        case FinishReason.Length:
            total_prompt_length = reduce(lambda acc, message: acc + len(message.content), messages, 0)

            logger.error(
                "Finished with reason Length",
                extra={
                    "message_id": reply_id,
                    "model": model.id,
                    "host": model.host,
                    "finish_reason": finish_reason,
                    "prompt_length": total_prompt_length,
                    "event": "inference.stream-error",
                },
            )
            err = (
                "the conversation is too large for the model to process, please shorten the conversation and try again"
            )
            yield MessageStreamError(message=reply_id, error=err, reason=finish_reason)

        case FinishReason.Aborted:
            logger.error(
                "Finished with reason Aborted",
                extra={
                    "message_id": reply_id,
                    "model": model.id,
                    "host": model.host,
                    "finish_reason": finish_reason,
                    "event": "inference.stream-error",
                },
            )
            err = "inference aborted for an unknown reason"
            yield MessageStreamError(message=reply_id, error=err, reason=finish_reason)

        case FinishReason.ModelOverloaded:
            logger.error(
                "Finished with reason ModelOverloaded",
                extra={
                    "message_id": reply_id,
                    "model": model.id,
                    "host": model.host,
                    "finish_reason": finish_reason,
                    "event": "inference.stream-error",
                },
            )
            yield MessageStreamError(
                message=reply_id,
                error="model overloaded",
                reason=FinishReason.ModelOverloaded,
            )

        case FinishReason.Stop:
            # This isn't an error
            pass

    return StreamMetrics(
        first_chunk_ns=first_chunk_ns,
        input_token_count=input_token_count,
        output_token_count=output_token_count,
        total_generation_ns=time_ns() - start_generation_ns,
    )
