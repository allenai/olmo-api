from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from pydantic import model_validator

import core.object_id as obj
from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.db.sqlalchemy_engine import SessionDependency
from api.service_errors import NotFoundError
from api.thread.models.flat_message import FlatMessage
from core.api_interface import APIInterface
from core.label.label import Label as LabelInterface
from core.label.rating import EXCLUSIVE_RATINGS, Rating
from db.models.label import Label


class LabelRequest(APIInterface):
    rating: Rating
    comment: str | None = None


LabelComparable = Label | LabelInterface | LabelRequest


class LabelCreateRequest(APIInterface):
    labels: list[LabelRequest]

    @model_validator(mode="after")
    def validate_binary_ratings(self) -> "LabelCreateRequest":
        request_exclusive_ratings = {label.rating for label in self.labels if label.rating in EXCLUSIVE_RATINGS}
        if Rating.POSITIVE in request_exclusive_ratings and Rating.NEGATIVE in request_exclusive_ratings:
            msg = "Cannot have both up and down ratings in the same request"
            raise ValueError(msg)
        return self


class LabelCreateService:
    def __init__(self, session: SessionDependency, message_repository: AsyncMessageRepositoryDependency):
        self.session = session
        self.message_repository = message_repository

    async def create(self, message_id: obj.ID, request: LabelCreateRequest, user_id: str) -> FlatMessage:
        async with self.session.begin():
            message = await self.message_repository.get_message_by_id(message_id, label_creator=user_id)

            if message is None:
                not_found_msg = f"Message with id `{message_id}` not found"
                raise NotFoundError(not_found_msg)

            existing_labels = [label for label in message.labels if label.creator == user_id and not label.deleted]

            # set labels to deleted if they dont exist in the request
            for existing_label in existing_labels:
                if not any(self.equal_value(existing_label, req_label) for req_label in request.labels):
                    existing_label.deleted = datetime.now(tz=UTC)

            # add labels from the request if they are different from existing labels
            for request_label in request.labels:
                if not any(self.equal_value(request_label, existing_label) for existing_label in existing_labels):
                    new_label = Label(
                        message=message.id,
                        rating=request_label.rating,
                        comment=request_label.comment,
                        creator=user_id,
                    )
                    self.session.add(new_label)

            await self.session.flush()

            # expire so that we can re-fetch the message
            self.session.expire(message)

            # fetch message with tools filtered
            # children joined for validation (children => child_id)
            message = await self.message_repository.get_message_by_id(
                message_id, include_children=True, label_creator=user_id
            )

            valid_message = FlatMessage.model_validate(message)

        return valid_message

    @classmethod
    def equal_value(cls, a: LabelComparable, b: LabelComparable) -> bool:
        return a.rating == b.rating and a.comment == b.comment


LabelCreateServiceDependency = Annotated[LabelCreateService, Depends()]
