from typing import Optional, Self, Sequence

from flask_pydantic_api.utils import UploadedFile
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.api_interface import APIInterface
from src.dao.message import (
    InferenceOpts,
    Message,
    Role,
    logprobs,
    max_tokens,
    num,
    temperature,
    top_p,
)


class CreateMessageRequest(APIInterface):
    # TODO: Validate that the parent role is different from this role and that it exists
    parent: Optional[str] = Field(default=None)
    max_tokens: int = Field(
        default=max_tokens.default,
        ge=max_tokens.min,
        le=max_tokens.max,
        multiple_of=max_tokens.step,
    )
    temperature: float = Field(
        default=temperature.default,
        ge=temperature.min,
        le=temperature.max,
        multiple_of=temperature.step,
    )
    n: int = Field(default=num.default, ge=num.min, le=num.max, multiple_of=num.step)
    top_p: float = Field(
        default=top_p.default, ge=top_p.min, le=top_p.max, multiple_of=top_p.step
    )
    logprobs: Optional[int] = Field(
        default=logprobs.default,
        ge=logprobs.min,
        le=logprobs.max,
        multiple_of=logprobs.step,
    )
    content: str = Field(min_length=1)
    role: Role
    original: Optional[str] = Field(default=None)
    private: bool = Field(default=False)
    template: Optional[str] = Field(default=None)
    model_id: str
    host: str

    @model_validator(mode="after")
    def check_original_and_parent_are_different(self) -> Self:
        if self.original is not None and self.parent == self.original:
            raise ValueError("The original message cannot also be the parent")

        return self

    @model_validator(mode="after")
    def check_assistant_message_has_a_parent(self) -> Self:
        if self.role is Role.Assistant and self.parent is None:
            raise ValueError("Assistant messages must have a parent")

        return self


class CreateMessageRequestWithLists(CreateMessageRequest):
    stop: Optional[list[str]] = Field(default=None)
    files: Optional[list[UploadedFile]] = Field(default=None)


class CreateMessageRequestWithFullMessages(BaseModel):
    parent_id: Optional[str] = Field(default=None)
    parent: Optional[Message] = Field(default=None)
    opts: InferenceOpts = Field(default_factory=InferenceOpts)
    content: str = Field(min_length=1)
    role: Role
    original: Optional[str] = Field(default=None)
    private: bool
    root: Optional[Message] = Field(default=None)
    template: Optional[str] = Field(default=None)
    model: str
    host: str
    files: Optional[Sequence[UploadedFile]] = Field(default=None)

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def parent_exists_if_parent_id_is_set(self) -> Self:
        if self.parent_id is not None and self.parent is None:
            raise ValueError(f"Parent message {self.parent_id} not found")

        return self

    @model_validator(mode="after")
    def root_exists_when_root_id_is_defined_with_no_parent(self) -> Self:
        if self.parent is not None and self.root is None:
            raise ValueError(f"Message has an invalid root {self.parent.root}")

        return self

    @model_validator(mode="after")
    def assistant_message_has_a_parent(self) -> Self:
        if self.role == Role.Assistant and self.parent is None:
            raise ValueError("Assistant messages must have a parent")

        return self

    @model_validator(mode="after")
    def parent_and_child_have_different_roles(self) -> Self:
        if self.parent is not None and self.parent.role == self.role:
            raise ValueError("Parent and child must have different roles")

        return self

    @model_validator(mode="after")
    def original_message_and_parent_are_different(self) -> Self:
        if (
            self.original is not None
            and self.parent_id is not None
            and self.original == self.parent_id
        ):
            raise ValueError("Original and parent messages must be different")

        return self

    @model_validator(mode="after")
    def private_matches_root_private(self) -> Self:
        if self.root is not None and self.root.private != self.private:
            raise ValueError(
                "Visibility must be identical for all messages in a thread"
            )

        return self
