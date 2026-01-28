from typing import Annotated, cast

from fastapi import Depends
from sqlalchemy import CursorResult, select, update

from api.db.sqlalchemy_engine import SessionDependency
from core.api_interface import APIInterface
from core.auth.token import Token
from db.models.label import Label
from db.models.message import Message
from db.models.user import User


class UserMigrationRequest(APIInterface):
    anonymous_user_client: str
    auth_user_client: str


class UserMigrationResponse(APIInterface):
    updated_user: User | None
    messages_updated_count: int


class UserMigrationService:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def migrate_user_from_anonymous_user(
        self,
        request: UserMigrationRequest,
        token: Token,
    ) -> UserMigrationResponse:
        if token.client != request.anonymous_user_client:
            msg = "Token client does not match anonymous user client."
            raise PermissionError(msg)

        stmt = select(User).where(User.client == request.anonymous_user_client)
        result = await self.session.scalars(stmt)
        anon_user = result.one_or_none()

        stmt = select(User).where(User.client == request.auth_user_client)
        result = await self.session.scalars(stmt)
        auth_user = result.one_or_none()

        updated_user = None

        if anon_user is not None and auth_user is not None:
            anon_user.id = auth_user.id
            anon_user.client = auth_user.client
            anon_user.terms_accepted_date = max(anon_user.terms_accepted_date, auth_user.terms_accepted_date)
            anon_user.acceptance_revoked_date = max(
                d
                for d in [
                    anon_user.acceptance_revoked_date,
                    auth_user.acceptance_revoked_date,
                ]
                if d is not None
            )
            anon_user.data_collection_accepted_date = max(
                d
                for d in [
                    anon_user.data_collection_accepted_date,
                    auth_user.data_collection_accepted_date,
                ]
                if d is not None
            )
            anon_user.data_collection_acceptance_revoked_date = max(
                d
                for d in [
                    anon_user.data_collection_acceptance_revoked_date,
                    auth_user.data_collection_acceptance_revoked_date,
                ]
                if d is not None
            )
            anon_user.media_collection_accepted_date = max(
                d
                for d in [
                    anon_user.media_collection_accepted_date,
                    auth_user.media_collection_accepted_date,
                ]
                if d is not None
            )
            anon_user.media_collection_acceptance_revoked_date = max(
                d
                for d in [
                    anon_user.media_collection_acceptance_revoked_date,
                    auth_user.media_collection_acceptance_revoked_date,
                ]
                if d is not None
            )

        elif anon_user is not None and auth_user is None:
            created_user = User(
                client=request.auth_user_client,
                terms_accepted_date=anon_user.terms_accepted_date,
                acceptance_revoked_date=anon_user.acceptance_revoked_date,
                data_collection_accepted_date=anon_user.data_collection_accepted_date,
                data_collection_acceptance_revoked_date=anon_user.data_collection_acceptance_revoked_date,
                media_collection_accepted_date=anon_user.media_collection_accepted_date,
                media_collection_acceptance_revoked_date=anon_user.media_collection_acceptance_revoked_date,
            )

            self.session.add(created_user)
            await self.session.flush()

            updated_user = created_user

        elif anon_user is None and auth_user is not None:
            updated_user = auth_user

        updated_messages_count = await self.migrate_messages_to_new_user(
            previous_user_id=request.anonymous_user_client, new_user_id=request.auth_user_client
        )

        return UserMigrationResponse.model_validate({
            "updated_user": updated_user,
            "messages_updated_count": updated_messages_count,
        })

    async def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str):
        await self.session.execute(update(Label).where(Label.creator == previous_user_id).values(creator=new_user_id))
        result = await self.session.execute(
            update(Message)
            .where(Message.creator == previous_user_id)
            .values(creator=new_user_id, expiration_time=None, private=False)
        )
        # cast is recommended by SQLAlchemy for this: https://github.com/sqlalchemy/sqlalchemy/issues/12913
        count = cast(CursorResult, result).rowcount
        await self.session.flush()
        await self.session.commit()

        return count

    async def get_by_creator(self, creator_id: str):
        stmt = select(Message).where(Message.creator == creator_id)
        result = await self.session.scalars(stmt)
        return result.unique().all()

UserMigrationServiceDependency = Annotated[UserMigrationService, Depends()]
