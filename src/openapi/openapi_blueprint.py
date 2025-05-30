from typing import Any

from flask import Blueprint, render_template
from flask_pydantic_api.openapi import get_openapi_schema
from pydantic.json_schema import GenerateJsonSchema

from src.message.v5_message_blueprint import FlatMessage

openapi_blueprint = Blueprint("openapi", __name__, template_folder="templates")


@openapi_blueprint.get("/openapi.json")
def get_openapi_spec() -> dict[str, Any]:
    schema = get_openapi_schema(
        schema_generator=GenerateJsonSchema,
    )

    # HACK: FlatMessage is a response from the v5/message/stream endpoint. OpenAPI doesn't support typing streamed responses so we need to add the types here
    flat_message_schema = FlatMessage.model_json_schema(ref_template="#/components/schemas/{model}")
    flat_message_schema_defs = flat_message_schema.pop("$defs")
    schema["components"]["schemas"] = {
        **schema["components"]["schemas"],
        **flat_message_schema_defs,
        FlatMessage.__name__: flat_message_schema,
    }
    return schema


@openapi_blueprint.get("/docs")
def get_apidocs() -> str:
    return render_template("rapidoc.html")
