import base64
import dataclasses
import json
import multiprocessing
import multiprocessing.pool
import os
from collections.abc import Generator, Sequence
from datetime import UTC, datetime, timedelta
from time import time_ns
from typing import cast

import grpc
from flask import current_app
from flask import request as flask_request
from werkzeug import exceptions
from werkzeug.datastructures import FileStorage

from src import db, parse, util
from src.auth.auth_service import authn
from src.bot_detection.create_assessment import create_assessment
from src.config.get_config import cfg
from src.config.get_models import get_model_by_host_and_id
from src.dao import completion, message
from src.inference.InferDEngine import InferDEngine
from src.inference.InferenceEngine import (
    FinishReason,
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
)
from src.inference.ModalEngine import ModalEngine
from src.message.create_message_request import (
    CreateMessageRequestV3,
    CreateMessageRequestV4WithLists,
    CreateMessageRequestWithFullMessages,
)
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.GoogleModerateText import GoogleModerateText
from src.message.GoogleVisionSafeSearch import GoogleVisionSafeSearch
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckerType,
    SafetyCheckRequest,
)
from src.message.validate_message_files_from_config import validate_message_files_from_config
from src.message.WildGuard import WildGuard


def check_message_safety(
    text: str,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
) -> bool | None:
    safety_checker: SafetyChecker = GoogleModerateText()
    request = SafetyCheckRequest(content=text)

    if checker_type == SafetyCheckerType.WildGuard:
        safety_checker = WildGuard()

    try:
        result = safety_checker.check_request(request)

        return result.is_safe()

    except Exception as e:
        current_app.logger.exception("Skipped message safety check due to error: %s. ", repr(e))

    return None


def check_image_safety(files: Sequence[FileStorage]) -> bool | None:
    checker = GoogleVisionSafeSearch()

    for file in files:
        try:
            image = base64.b64encode(file.stream.read()).decode("utf-8")
            file.stream.seek(0)

            request = SafetyCheckRequest(image, file.filename)
            result = checker.check_request(request)

            if not result.is_safe():
                return False

        except Exception as e:
            current_app.logger.exception(
                "Skipped image safety check over %s due to error: %s. ",
                file.filename,
                repr(e),
            )

            return None

    return True


@dataclasses.dataclass
class ParsedMessage:
    content: parse.MessageContent
    role: message.Role


def get_engine(host: str) -> InferenceEngine:
    match host:
        case "inferd":
            return InferDEngine()
        case "modal" | _:
            return ModalEngine()


def upload_request_files(
    files: Sequence[FileStorage] | None,
    message_id: str,
    storage_client: GoogleCloudStorage,
    root_message_id: str,
    is_anonymous: bool = False,
) -> list[str] | None:
    if files is None or len(files) == 0:
        return None

    file_urls: list[str] = []

    for i, file in enumerate(files):
        file_extension = os.path.splitext(file.filename)[1] if file.filename is not None else ""

        # We don't want to save filenames since we're not safety checking them for dangerous or personal info
        filename = f"{root_message_id}/{message_id}-{i}{file_extension}"

        if file.content_type is None:
            file_url = storage_client.upload_content(
                filename=filename, content=file.stream.read(), is_anonymous=is_anonymous
            )
        else:
            file_url = storage_client.upload_content(
                filename=filename, content=file.stream.read(), content_type=file.content_type, is_anonymous=is_anonymous
            )

        # since we read from the file we need to rewind it so the next consumer can read it
        file.stream.seek(0)
        file_urls.append(file_url)

    return file_urls


def evaluate_prompt_submission_captcha(
    captcha_token: str, user_ip_address: str | None, user_agent: str | None, *, is_anonymous_user: bool
):
    prompt_submission_action = "prompt_submission"
    if cfg.google_cloud_services.recaptcha_key is not None and captcha_token is not None:
        captcha_assessment = create_assessment(
            project_id="ai2-reviz",
            recaptcha_key=cfg.google_cloud_services.recaptcha_key,
            token=captcha_token,
            recaptcha_action=prompt_submission_action,
            user_ip_address=user_ip_address,
            user_agent=user_agent,
        )

        if not is_anonymous_user or not cfg.google_cloud_services.enable_recaptcha:
            return

        logger = current_app.logger

        if captcha_assessment is None or not captcha_assessment.token_properties.valid:
            logger.info("rejecting message request due to invalid captcha", extra={"assessment": captcha_assessment})
            invalid_captcha_message = "invalid_captcha"
            raise exceptions.BadRequest(invalid_captcha_message)

        if (
            captcha_assessment.risk_analysis.score == 0.0
            or captcha_assessment.token_properties is not prompt_submission_action
        ):
            logger.info(
                "rejecting message request due to failed captcha assessment", extra={"assessment": captcha_assessment}
            )
            failed_captcha_assessment_message = "failed_captcha_assessment"
            raise exceptions.BadRequest(failed_captcha_assessment_message)


def stream_new_message(
    request: CreateMessageRequestWithFullMessages,
    dbc: db.Client,
    storage_client: GoogleCloudStorage,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
    user_ip_address: str | None = None,
    user_agent: str | None = None,
) -> message.Message | Generator[str, None, None]:
    start_all = time_ns()
    agent = authn()

    inference_engine = get_engine(request.host)

    model = inference_engine.get_model_details(request.model)
    if not model:
        error_message = f"model {request.model} is not available on {request.host}"
        raise exceptions.BadRequest(error_message)

    evaluate_prompt_submission_captcha(
        request.captcha_token,
        user_ip_address=user_ip_address,
        user_agent=user_agent,
        is_anonymous_user=agent.is_anonymous_user,
    )

    is_content_safe = None
    is_image_safe = None
    # Capture the SHA and logger, as the current_app context is lost in the generator.
    sha = os.environ.get("SHA") or "DEV"
    logger = current_app.logger

    safety_check_elapsed_time = 0
    if request.role == message.Role.User:
        safety_check_start_time = time_ns()
        is_content_safe = check_message_safety(request.content, checker_type)
        is_image_safe = check_image_safety(request.files or [])
        safety_check_elapsed_time = (time_ns() - safety_check_start_time) // 1_000_000

        # We don't want to save messages from anonymous users
        # Not saving the completion is probably better than saving it with bad info
        if not agent.is_anonymous_user:
            dbc.completion.create(
                request.content,
                [
                    completion.CompletionOutput(
                        str(is_content_safe),
                        finish_reason=FinishReason.Stop,
                    )
                ],
                message.InferenceOpts(),
                checker_type,
                sha,
                tokenize_ms=-1,
                generation_ms=safety_check_elapsed_time,
                queue_ms=0,
                input_tokens=-1,
                output_tokens=-1,
            )

        if is_content_safe is False:
            raise exceptions.BadRequest(description="inappropriate_prompt_text")

        if is_image_safe is False:
            raise exceptions.BadRequest(description="inappropriate_prompt_file")

    # We currently want anonymous users' messages to expire after 1 days
    message_expiration_time = datetime.now(UTC) + timedelta(days=1) if agent.is_anonymous_user else None

    is_msg_harmful = None if is_content_safe is None or is_image_safe is None else False
    system_msg = None
    msg = None

    # if the request message is the first message in a thread
    if request.parent is None:
        # create a system prompt message if the current model is specified with a system prompt
        if model.system_prompt is not None:
            system_msg = dbc.message.create(
                content=model.system_prompt,
                creator=agent.client,
                role=message.Role.System,
                opts=request.opts,
                model_id=request.model,
                model_host=request.host,
                root=None,
                parent=None,
                template=request.template,
                final=False,
                original=request.original,
                private=request.private,
                harmful=is_msg_harmful,
                expiration_time=message_expiration_time,
            )

        parent_id = None if system_msg is None else system_msg.id

        msg = dbc.message.create(
            content=request.content,
            creator=agent.client,
            role=request.role,
            opts=request.opts,
            model_id=request.model,
            model_host=request.host,
            root=parent_id,
            parent=parent_id,
            template=request.template,
            final=request.role == message.Role.Assistant,
            original=request.original,
            private=request.private,
            harmful=is_msg_harmful,
            expiration_time=message_expiration_time,
        )
    else:
        msg = dbc.message.create(
            content=request.content,
            creator=agent.client,
            role=request.role,
            opts=request.opts,
            model_id=request.model,
            model_host=request.host,
            root=request.parent.root,
            parent=request.parent.id,
            template=request.template,
            final=request.role == message.Role.Assistant,
            original=request.original,
            private=request.private,
            harmful=is_msg_harmful,
            expiration_time=message_expiration_time,
        )

    if msg.role == message.Role.Assistant:
        return msg

    # Resolve the message chain if we need to.
    message_chain = [msg]
    if request.root is not None:
        msgs = message.Message.group_by_id(request.root.flatten())
        while message_chain[-1].parent is not None:
            message_chain.append(msgs[message_chain[-1].parent])

    if system_msg is not None:
        message_chain.append(system_msg)

    message_chain.reverse()

    file_urls = upload_request_files(
        files=request.files,
        message_id=msg.id,
        storage_client=storage_client,
        root_message_id=message_chain[0].id,
        is_anonymous=agent.is_anonymous_user,
    )

    chain: list[InferenceEngineMessage] = [
        InferenceEngineMessage(
            role=message_in_chain.role,
            content=message_in_chain.content,
            # We only want to add the request files to the new message. The rest will have file urls associated with them
            files=request.files if message_in_chain.id == msg.id else message_in_chain.file_urls,
        )
        for message_in_chain in message_chain
    ]

    # TODO https://github.com/allenai/playground-issues-repo/issues/9: Get this from the DB
    msg.file_urls = file_urls

    # Create a message that will eventually capture the streamed response.
    # TODO: should handle exceptions mid-stream by deleting and/or finalizing the message
    reply = dbc.message.create(
        "",
        agent.client,
        message.Role.Assistant,
        msg.opts,
        model_id=request.model,
        model_host=request.host,
        root=msg.root,
        parent=msg.id,
        final=False,
        private=request.private,
        model_type=model.model_type,
        expiration_time=message_expiration_time,
    )

    # Update the parent message to include the reply.
    msg = dataclasses.replace(msg, children=[reply])

    # Update system prompt to include user message as a child.
    if system_msg is not None:
        system_msg = dataclasses.replace(system_msg, children=[msg])

    def stream() -> Generator[str, None, None]:
        # We keep track of each chunk and the timing information per-chunk
        # so that we can manifest a completion at the end. This will go
        # away when InferD stores this I/O.
        chunks: list[message.MessageChunk] = []
        start_gen = time_ns()

        # Yield the system prompt message if there is any
        if system_msg is not None:
            yield format_message(system_msg)
        # Yield the new user message
        else:
            yield format_message(msg)

        # Now yield each chunk as it's returned.
        finish_reason: FinishReason | None = None
        first_ns = 0
        chunk_count = 0
        input_token_count = -1
        output_token_count = -1

        def map_chunk(chunk: InferenceEngineChunk):
            # This tells python that we're referencing the variables from the closure and not making new ones
            nonlocal finish_reason, input_token_count, output_token_count, chunk_count, first_ns

            finish_reason = chunk.finish_reason

            chunk_logprobs = chunk.logprobs if chunk.logprobs is not None else []
            mapped_logprobs = [
                [message.TokenLogProbs(token_id=lp.token_id, text=lp.text, logprob=lp.logprob) for lp in lp_list]
                for lp_list in chunk_logprobs
            ]

            new_chunk = message.MessageChunk(
                message=reply.id,
                content=chunk.content,
                logprobs=mapped_logprobs,
            )
            chunks.append(new_chunk)

            input_token_count = chunk.input_token_count
            output_token_count = chunk.output_token_count
            chunk_count += 1
            first_ns = time_ns() if first_ns == 0 else first_ns

            return format_message(new_chunk)

        try:
            message_generator = inference_engine.create_streamed_message(
                model=model.compute_source_id,
                messages=chain,
                inference_options=InferenceOptions(**reply.opts.model_dump()),
            )

            # Adapted from https://anonbadger.wordpress.com/2018/12/15/python-signal-handlers-and-exceptions/
            pool = multiprocessing.pool.ThreadPool(processes=1)
            results = pool.apply_async(lambda: next(message_generator))

            # We handle the first chunk differently since we want to timeout if it takes longer than 5 seconds
            first_chunk = results.get(15.0)
            yield map_chunk(first_chunk)

            for chunk in message_generator:
                yield map_chunk(chunk)

        except grpc.RpcError as e:
            finish_reason = FinishReason.BadConnection
            err = f"inference failed: {e}"
            logger.exception(
                "GRPC inference failed",
                extra={
                    "message_id": reply.id,
                    "model": model.id,
                    "host": model.host,
                    "finish_reason": finish_reason,
                    "event": "inference.stream-error",
                },
            )
            yield format_message(message.MessageStreamError(reply.id, err, "grpc inference failed"))

        except multiprocessing.TimeoutError:
            finish_reason = FinishReason.ModelOverloaded

        except ValueError as e:
            finish_reason = FinishReason.ValueError
            logger.exception(
                "Value Error from inference",
                extra={
                    "message_id": reply.id,
                    "model": model.id,
                    "host": model.host,
                    "finish_reason": finish_reason,
                    "event": "inference.stream-error",
                },
            )
            # value error can be like when context length is too long
            yield format_message(message.MessageStreamError(reply.id, f"{e}", "value error from inference result"))

        except Exception as e:
            finish_reason = FinishReason.Unknown
            logger.exception(
                "Unexpected error during inference",
                extra={
                    "message_id": reply.id,
                    "model": model.id,
                    "host": model.host,
                    "finish_reason": finish_reason,
                    "event": "inference.stream-error",
                },
            )
            yield format_message(message.MessageStreamError(reply.id, f"{e}", "general exception"))

        match finish_reason:
            case FinishReason.UnclosedStream:
                logger.error(
                    "Finished with reason UnclosedStream",
                    extra={
                        "message_id": reply.id,
                        "model": model.id,
                        "host": model.host,
                        "finish_reason": finish_reason,
                        "event": "inference.stream-error",
                    },
                )
                err = "inference failed for an unknown reason: sometimes this happens when the prompt is too long"
                yield format_message(message.MessageStreamError(reply.id, err, finish_reason))

            case FinishReason.Length:
                logger.error(
                    "Finished with reason Length",
                    extra={
                        "message_id": reply.id,
                        "model": model.id,
                        "host": model.host,
                        "finish_reason": finish_reason,
                        "prompt_length": len(request.content),
                        "event": "inference.stream-error",
                    },
                )
                err = "the conversation is too large for the model to process, please shorten the conversation and try again"
                yield format_message(message.MessageStreamError(reply.id, err, finish_reason))

            case FinishReason.Aborted:
                logger.error(
                    "Finished with reason Aborted",
                    extra={
                        "message_id": reply.id,
                        "model": model.id,
                        "host": model.host,
                        "finish_reason": finish_reason,
                        "event": "inference.stream-error",
                    },
                )
                err = "inference aborted for an unknown reason"
                yield format_message(message.MessageStreamError(reply.id, err, finish_reason))

            case FinishReason.ModelOverloaded:
                logger.error(
                    "Finished with reason ModelOverloaded",
                    extra={
                        "message_id": reply.id,
                        "model": model.id,
                        "host": model.host,
                        "finish_reason": finish_reason,
                        "event": "inference.stream-error",
                    },
                )
                yield format_message(
                    message.MessageStreamError(
                        message=reply.id,
                        error="model overloaded",
                        reason=FinishReason.ModelOverloaded,
                    )
                )

            case FinishReason.Stop:
                # This isn't an error
                pass

        # The generation is complete. Store it.
        # TODO: InferD should store this so that we don't have to.
        # TODO: capture InferD request input instead of our manifestation of the prompt format

        gen = time_ns() - start_gen
        gen //= 1000000

        prompt = create_prompt_from_engine_input(chain)
        output, logprobs = create_output_from_chunks(chunks)

        message_completion = None
        if not agent.is_anonymous_user:
            message_completion = dbc.completion.create(
                prompt,
                [completion.CompletionOutput(output, str(finish_reason), logprobs)],
                msg.opts,
                model.compute_source_id,
                sha,
                tokenize_ms=-1,
                generation_ms=gen,
                queue_ms=0,
                input_tokens=input_token_count,
                output_tokens=output_token_count,
            )

        # Finalize the messages and yield
        final_message = dbc.message.finalize(msg.id, file_urls=file_urls)
        if final_message is None:
            final_message_error = RuntimeError(f"failed to finalize message {msg.id}")
            yield format_message(message.MessageStreamError(msg.id, str(final_message_error), "finalization failure"))
            raise final_message_error

        final_reply = dbc.message.finalize(
            reply.id,
            output,
            logprobs,
            message_completion.id if message_completion is not None else None,
            finish_reason,
        )
        if final_reply is None:
            final_reply_error = RuntimeError(f"failed to finalize message {reply.id}")
            yield format_message(message.MessageStreamError(reply.id, str(final_reply_error), "finalization failure"))
            raise final_reply_error

        final_message = dataclasses.replace(final_message, children=[final_reply])

        if system_msg is not None:
            finalSystemMessage = dbc.message.finalize(system_msg.id)

            if finalSystemMessage is None:
                final_system_message_error = RuntimeError(f"failed to finalize message {system_msg.id}")
                yield format_message(
                    message.MessageStreamError(
                        system_msg.id,
                        str(final_system_message_error),
                        "finalization failure",
                    )
                )
                raise final_system_message_error

            finalSystemMessage = dataclasses.replace(finalSystemMessage, children=[final_message])
            final_message = finalSystemMessage

        end_all = time_ns()
        if first_ns > start_all:
            logger.info({
                "event": "inference.timing",
                "ttft_ms": (first_ns - start_all) // 1e6,
                "total_ms": (end_all - start_all) // 1e6,
                "safety_ms": safety_check_elapsed_time,
                "input_tokens": input_token_count,
                "output_tokens": output_token_count,
                "sha": sha,
                "model": model.id,
                "safety_check_id": checker_type,
                "message_id": msg.id,
                "reply_id": reply.id,
                "remote_address": user_ip_address,
            })

        yield format_message(final_message)

    return stream()


def get_parent_and_root_messages_and_private(
    parent_message_id: str | None,
    dbc: db.Client,
    request_private: bool | None,
    is_anonymous_user: bool,
) -> tuple[message.Message | None, message.Message | None, bool]:
    parent_message = dbc.message.get(parent_message_id) if parent_message_id is not None else None
    root_message = dbc.message.get(parent_message.root) if parent_message is not None else None

    private = (
        # Anonymous users aren't allowed to share messages
        True
        if is_anonymous_user
        else (
            request_private
            if request_private is not None
            else root_message.private
            if root_message is not None
            else False
        )
    )

    return parent_message, root_message, private


def create_message_v3(
    request: CreateMessageRequestV3,
    dbc: db.Client,
    storage_client: GoogleCloudStorage,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
) -> message.Message | Generator[str, None, None]:
    agent = authn()

    parent_message, root_message, private = get_parent_and_root_messages_and_private(
        request.parent, dbc, request.private, is_anonymous_user=agent.is_anonymous_user
    )

    mapped_request = CreateMessageRequestWithFullMessages(
        parent_id=request.parent,
        parent=parent_message,
        opts=request.opts,
        content=request.content,
        role=cast(message.Role, request.role),
        original=request.original,
        private=private,
        root=root_message,
        template=request.template,
        model=request.model,
        host=request.host,
        client=agent.client,
        captcha_token=request.captcha_token,
    )

    user_ip_address = flask_request.remote_addr
    user_agent = flask_request.user_agent.string

    return stream_new_message(
        mapped_request,
        dbc,
        storage_client=storage_client,
        checker_type=checker_type,
        user_ip_address=user_ip_address,
        user_agent=user_agent,
    )


def create_message_v4(
    request: CreateMessageRequestV4WithLists,
    dbc: db.Client,
    storage_client: GoogleCloudStorage,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
) -> message.Message | Generator[str, None, None]:
    agent = authn()

    parent_message, root_message, private = get_parent_and_root_messages_and_private(
        request.parent, dbc, request.private, is_anonymous_user=agent.is_anonymous_user
    )

    mapped_request = CreateMessageRequestWithFullMessages(
        parent_id=request.parent,
        parent=parent_message,
        opts=message.InferenceOpts(
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            n=request.n,
            top_p=request.top_p,
            logprobs=request.logprobs,
            stop=request.stop,
        ),
        content=request.content,
        role=cast(message.Role, request.role),
        original=request.original,
        private=private,
        root=root_message,
        template=request.template,
        model=request.model,
        host=request.host,
        client=agent.client,
        files=request.files,
        captcha_token=request.captcha_token,
    )

    model_config = get_model_by_host_and_id(mapped_request.host, mapped_request.model)
    validate_message_files_from_config(request.files, config=model_config, has_parent=mapped_request.parent is not None)

    user_ip_address = flask_request.remote_addr
    user_agent = flask_request.user_agent.string

    return stream_new_message(
        mapped_request,
        dbc,
        storage_client=storage_client,
        checker_type=checker_type,
        user_ip_address=user_ip_address,
        user_agent=user_agent,
    )


def format_message(obj) -> str:
    return json.dumps(obj=obj, cls=util.CustomEncoder) + "\n"


def format_prompt(message: InferenceEngineMessage) -> str:
    return f"<|{message.role}|>\n{message.content}"


def create_prompt_from_engine_input(
    input_list: list[InferenceEngineMessage],
) -> str:
    return "\n".join([format_prompt(m) for m in input_list])


def create_output_from_chunks(chunks: list[message.MessageChunk]):
    output = ""
    logprobs: list[list[message.TokenLogProbs]] = []

    for chunk in chunks:
        output += chunk.content
        if chunk.logprobs is not None and len(chunk.logprobs) > 0:
            logprobs.append(*chunk.logprobs)

    return output, logprobs
