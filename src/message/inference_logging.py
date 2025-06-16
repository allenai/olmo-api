import os

from flask import current_app
from flask import request as flask_request


def log_inference_timing(
    event_type: str, ttft_ns: int, total_ns: int, input_token_count: int, output_token_count: int, model: str, **kwargs
):
    logger = current_app.logger
    ttft_ms = ttft_ns // 1e6
    total_ms = total_ns // 1e6
    remote_address = flask_request.remote_addr

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
