from pydantic import BaseModel, Field


class InferenceOpts(BaseModel):
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stop: list[str] | None = None

    # NOTE: defaults set on these two fields as they don't have defaults set in the DB model_config

    # n has a max of 1 when streaming. if we allow for non-streaming requests we can go up to 50
    n: int = Field(default=1, ge=1, le=1)
    logprobs: int | None = Field(default=None, ge=0, le=10)
