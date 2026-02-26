import json
import time
from collections.abc import Generator

from flask import Blueprint, Response, request, stream_with_context
from src.flask_pydantic_api.api_wrapper import pydantic_api


def generate_chunks(num: int, delay: float) -> Generator[str, None, None]:
    for i in range(num):
        time.sleep(delay / 1000)
        yield json.dumps({"chunk": i}) + "\n"

def create_fake_request_blueprint() -> Blueprint:
    fake_request_blueprint = Blueprint("fake-request", __name__)

    @fake_request_blueprint.get("")
    @pydantic_api(name="fake-request")
    def fake_response() -> Response:
        num = int(request.args.get("num", 10))
        delay = float(request.args.get("delay", 100.0))

        return Response(stream_with_context(generate_chunks(num, delay)), mimetype="application/jsonl")

    return fake_request_blueprint
