import logging
import os

logger = logging.getLogger(__name__)


def log_inference_timing(
    event_type: str,
    ttft_ns: int,
    total_ns: int,
    input_token_count: int,
    output_token_count: int,
    model: str,
    remote_address: str | None = None,
    **kwargs,
):
    ttft_ms = ttft_ns // 1e6
    total_ms = total_ns // 1e6

    event_log = dict(
        event="inference.timing",
        event_type=event_type,
        sha=os.environ.get("SHA", "DEV"),
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        model=model,
        input_tokens=input_token_count,
        output_tokens=output_token_count,
        remote_address=remote_address,
        **kwargs,
    )

    logger.info(event_log)
