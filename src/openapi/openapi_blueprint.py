from typing import Any

from flask import Blueprint, render_template
from flask_pydantic_api.openapi import get_openapi_schema
from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, models_json_schema

from src.message.message_chunk import BaseChunk

openapi_blueprint = Blueprint("openapi", __name__, template_folder="templates")

REF_TEMPLATE = "#/components/schemas/{model}"


@openapi_blueprint.get("/openapi.json")
def get_openapi_spec() -> dict[str, Any]:
    schema = get_openapi_schema(
        schema_generator=GenerateJsonSchema,
    )

    # HACK: These are responses from the message streaming endpoint. OpenAPI doesn't support typing streamed responses so we need to add the types here
    chunks: list[tuple[type[BaseModel], JsonSchemaMode]] = [
        (subclass, "serialization") for subclass in BaseChunk.__subclasses__()
    ]
    _, top_level_schema = models_json_schema(chunks, ref_template=REF_TEMPLATE)

    schema["components"]["schemas"].update(top_level_schema.get("$defs"))

    return schema


@openapi_blueprint.get("/docs")
def get_apidocs() -> str:
    return render_template("rapidoc.html")
