from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

import core.object_id as obj
from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.db.sqlalchemy_engine import SessionDependency
from api.service_errors import ForbiddenError, NotFoundError
from core.label.label import Label as LabelInterface
from db.models.label import Label


class LabelDeleteService:
    def __init__(self, session: SessionDependency, message_repository: AsyncMessageRepositoryDependency):
        self.session = session
        self.message_repository = message_repository

    async def delete_one(self, label_id: obj.ID, user_id: obj.ID) -> LabelInterface:
        async with self.session.begin():
            label_stmt = select(Label).where(Label.id == label_id)
            label = await self.session.scalar(label_stmt)

            if label is None:
                not_found_msg = f"Label with id `{label_id}` was not found."
                raise NotFoundError(not_found_msg)

            if user_id != label.creator:
                forbidden_msg = "Label can only be deleted by its creator"
                raise ForbiddenError(forbidden_msg)

            label.deleted = datetime.now(tz=UTC)

            await self.session.flush()

            return LabelInterface.model_validate(label)


LabelDeleteServiceDependency = Annotated[LabelDeleteService, Depends()]
