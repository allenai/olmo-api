from pydantic import Field, field_validator

from api.attribution.response_attribution_document import ResponseAttributionDocument
from api.attribution.response_attribution_span import TopLevelAttributionSpan
from core.api_interface import APIInterface


class GetAttributionRequest(APIInterface):
    prompt: str
    model_response: str
    model_id: str
    max_documents: int = Field(default=10)  # unused (we pass this in the ui request) ??
    max_display_context_length: int = Field(default=250)

    @field_validator("prompt", mode="after")
    @classmethod
    def should_block_prompt(cls, prompt: str) -> str:
        if "lyric" in prompt.lower() or "song" in prompt.lower():
            msg = "The prompt is blocked due to legal compliance."
            raise ValueError(msg)
        return prompt


class AttributionResponse(APIInterface):
    index: str
    documents: list[ResponseAttributionDocument]
    spans: list[TopLevelAttributionSpan]
