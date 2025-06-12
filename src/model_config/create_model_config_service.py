from typing import Literal

from psycopg.errors import UniqueViolation
from pydantic import AwareDatetime, ByteSize, Field, RootModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src.api_interface import APIInterface
from src.config.ModelConfig import (
    FileRequiredToPromptOption,
    ModelHost,
    ModelType,
)
from src.dao.engine_models.model_config import (
    PromptType,
)
from src.model_config.model_config_utils import get_model_config_class
from src.model_config.response_model import ResponseModel


class BaseCreateModelConfigRequest(APIInterface):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    host: ModelHost
    description: str = Field(min_length=1)
    model_type: ModelType
    model_id_on_host: str = Field(min_length=1)
    internal: bool = Field(default=True)
    default_system_prompt: str | None = Field(default=None)
    family_id: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    available_time: AwareDatetime | None = Field(default=None)
    deprecation_time: AwareDatetime | None = Field(default=None)


class CreateTextOnlyModelConfigRequest(BaseCreateModelConfigRequest):
    prompt_type: Literal[PromptType.TEXT_ONLY]


class CreateMultiModalModelConfigRequest(BaseCreateModelConfigRequest):
    prompt_type: Literal[PromptType.MULTI_MODAL, PromptType.FILES_ONLY]
    accepted_file_types: list[str]
    max_files_per_message: int | None = Field(default=None)
    require_file_to_prompt: FileRequiredToPromptOption | None = Field(default=None)
    max_total_file_size: ByteSize | None = Field(default=None)
    allow_files_in_followups: bool | None = Field(default=None)


# We can't make a discriminated union at the top level so we need to use a RootModel
class RootCreateModelConfigRequest(RootModel):
    root: CreateTextOnlyModelConfigRequest | CreateMultiModalModelConfigRequest = Field(discriminator="prompt_type")


def create_model_config(request: RootCreateModelConfigRequest, session_maker: sessionmaker[Session]) -> ResponseModel:
    with session_maker.begin() as session:
        try:
            RequestClass = get_model_config_class(request.root)  # noqa: N806

            new_model = RequestClass(**request.model_dump(by_alias=False))
            # TODO: There's a bug here where this request returns the available and deprecation times in the time zone that was submitted. It should return as UTC, which is what it gets saved as in the DB
            session.add(new_model)
            session.flush()

            return ResponseModel.model_validate(new_model)

        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                conflict_message = f"{request.root.id} already exists"
                raise exceptions.Conflict(conflict_message) from e

            raise
