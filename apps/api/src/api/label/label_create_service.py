from typing import Annotated

from fastapi import Depends

import core.object_id as obj
from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.db.sqlalchemy_engine import SessionDependency
from api.service_errors import NotFoundError, ResourceExistsError
from core.api_interface import APIInterface
from core.label.label import Label as LabelInterface
from db.models.label import Label

label_id_generator = obj.new_id_generator("lbl")


class LabelCreateRequest(APIInterface):
    # id: str | None = None
    message: str
    rating: int
    comment: str | None = None


class LabelCreateService:
    def __init__(self, session: SessionDependency, message_repository: AsyncMessageRepositoryDependency):
        self.session = session
        self.message_repository = message_repository

    async def create(self, request: LabelCreateRequest, user_id: str):
        async with self.session.begin():
            message = await self.message_repository.get_message_by_id(request.message)

            if message is None:
                not_found_msg = f"Message with id `{request.message}` not found"
                raise NotFoundError(not_found_msg)

            existing_labels = [label for label in message.labels if label.creator == user_id and not label.deleted]

            if len(existing_labels) != 0:
                label_exists_msg = f"Label already exists for Message id ${request.message}"
                raise ResourceExistsError(label_exists_msg)

            new_label = Label(
                id=label_id_generator(),
                message=request.message,  # message.id ?
                rating=request.rating,
                creator=user_id,  # message.creator ?
                comment=request.comment,
            )

            self.session.add(new_label)
            await self.session.flush()

            return LabelInterface.model_validate(new_label)


LabelCreateServiceDependency = Annotated[LabelCreateService, Depends()]
