from typing import Optional, Self, Sequence

from flask_pydantic_api.utils import UploadedFile
from pydantic import BaseModel, Field, model_validator
from werkzeug.datastructures import FileStorage

from src.api_interface import APIInterface
from src.dao.message import InferenceOpts, Message, Role


class CreateMessageRequest(APIInterface):
    # TODO: Validate that the parent role is different from this role and that it exists
    parent: Optional[str] = Field(default=None)
    max_tokens: int
    temperature: float
    n: int = Field(default=1, ge=1, le=1, multiple_of=1)
    top_p: float = Field(default=1.0, ge=0.01, le=1.0, multiple_of=0.01)
    logprobs: Optional[int] = Field(default=None, ge=0, le=10, multiple_of=1)
    # Mapping for this is handled in the controller
    content: str = Field(min_length=1)
    role: Role
    original: Optional[str] = Field(default=None)
    private: bool
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
    opts: InferenceOpts
    content: str = Field(min_length=1)
    role: Role
    original: Optional[str] = Field(default=None)
    private: bool
    root: Optional[Message] = Field(default=None)
    template: Optional[str] = Field(default=None)
    model_id: str
    host: str
    files: Optional[Sequence[FileStorage]] = Field(default=None)

    @model_validator(mode="after")
    def parent_exists_if_parent_id_is_set(self) -> Self:
        if self.parent_id is not None and self.parent is None:
            raise ValueError(f"Parent message {self.parent_id}")

        return self

    @model_validator(mode="after")
    def root_exists_when_root_id_is_defined_with_no_parent(self) -> Self:
        if self.parent is not None:
            if self.root is None:
                raise ValueError(f"Message has an invalid root {self.parent.root}")

        return self
