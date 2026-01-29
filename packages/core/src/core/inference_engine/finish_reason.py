from enum import StrEnum


class FinishReason(StrEnum):
    # Something caused the generation to be left incomplete. The only scenario where this happens
    # (that we know of) is when the prompt is too long and it's the only item being process (batch
    # size is 1):
    # See: https://github.com/allenai/inferd-tulu2/blob/main/src/svllm.py#L106
    UnclosedStream = "unclosed stream"

    # The model stopped because max_tokens was reached, or because the prompt was too long and
    # there were several items in the batch.
    Length = "length"

    # The model generated a response and stopped before max_tokens was reached.
    Stop = "stop"

    # The generation was aborted for an unknown reason.
    Aborted = "aborted"

    # The model took longer than our timeout to return the first token
    ModelOverloaded = "model overloaded"

    # Encountered RPC error from inferD
    BadConnection = "bad connection"

    # Value error can be like when context length is too long
    ValueError = "value error"

    # Something related to tools had an error
    ToolError = "tool error"

    # General exceptions
    Unknown = "unknown"
