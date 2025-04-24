from typing import Any

from flask import Blueprint, render_template
from flask_pydantic_api.openapi import get_openapi_schema
from pydantic.json_schema import GenerateJsonSchema

openapi_blueprint = Blueprint("openapi", __name__, template_folder="templates")


@openapi_blueprint.get("/openapi.json")
def get_openapi_spec() -> dict[str, Any]:
    schema = get_openapi_schema(schema_generator=GenerateJsonSchema)
    return schema


@openapi_blueprint.get("/docs")
def get_apidocs() -> str:
    return render_template("rapidoc.html")
