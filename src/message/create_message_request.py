from typing import Optional, Self

from flask_pydantic_api.utils import UploadedFile
from pydantic import Field, field_serializer, model_validator

from src.api_interface import APIInterface
from src.dao.message import Role


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
    root: Optional[str] = Field(default=None)
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

    # TODO: Remove this when we have real output
    @field_serializer("files")
    def serialize_files(self, files: Optional[list[UploadedFile]]):
        if files is not None:
            return [file.filename for file in files]
        else:
            return None
