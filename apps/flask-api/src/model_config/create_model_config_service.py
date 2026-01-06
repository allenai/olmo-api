from psycopg.errors import UniqueViolation
from pydantic import Field, RootModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from core.api_interface import APIInterface
from src.model_config.base_model_config import (
    BaseMultiModalModelConfigRequest,
    BaseTextOnlyModelConfigRequest,
)
from src.model_config.model_config_utils import get_model_config_class
from src.model_config.response_model import ResponseModel


class BaseCreateModelConfigRequest(APIInterface):
    id: str = Field(min_length=1)


class CreateTextOnlyModelConfigRequest(
    BaseCreateModelConfigRequest,
    BaseTextOnlyModelConfigRequest,
): ...


class CreateMultiModalModelConfigRequest(
    BaseCreateModelConfigRequest,
    BaseMultiModalModelConfigRequest,
): ...


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
