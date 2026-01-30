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
    anonymous_user_id: str


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
        anonymous_user_id = request.anonymous_user_id
        auth_user_client = token.client

        # Fetch anonymous user by client ID
        stmt = select(User).where(User.client == anonymous_user_id)
        result = await self.session.scalars(stmt)
        anon_user = result.one_or_none()

        # Fetch authenticated user by client ID
        stmt = select(User).where(User.client == auth_user_client)
        result = await self.session.scalars(stmt)
        auth_user = result.one_or_none()

        updated_user = None

        if anon_user is not None and auth_user is not None:
            # Merge t&c data into authenticated user, keeping the most recent dates
            auth_user.terms_accepted_date = max(
                anon_user.terms_accepted_date,
                auth_user.terms_accepted_date,
            )

            revoked_dates = [
                d
                for d in [
                    anon_user.acceptance_revoked_date,
                    auth_user.acceptance_revoked_date,
                ]
                if d is not None
            ]
            auth_user.acceptance_revoked_date = max(revoked_dates) if revoked_dates else None

            # Handle data collection dates
            data_collection_dates = [
                d
                for d in [
                    anon_user.data_collection_accepted_date,
                    auth_user.data_collection_accepted_date,
                ]
                if d is not None
            ]
            auth_user.data_collection_accepted_date = max(data_collection_dates) if data_collection_dates else None

            data_collection_revoked_dates = [
                d
                for d in [
                    anon_user.data_collection_acceptance_revoked_date,
                    auth_user.data_collection_acceptance_revoked_date,
                ]
                if d is not None
            ]
            auth_user.data_collection_acceptance_revoked_date = (
                max(data_collection_revoked_dates) if data_collection_revoked_dates else None
            )

            # Handle media collection dates
            media_collection_dates = [
                d
                for d in [
                    anon_user.media_collection_accepted_date,
                    auth_user.media_collection_accepted_date,
                ]
                if d is not None
            ]
            auth_user.media_collection_accepted_date = max(media_collection_dates) if media_collection_dates else None

            media_collection_revoked_dates = [
                d
                for d in [
                    anon_user.media_collection_acceptance_revoked_date,
                    auth_user.media_collection_acceptance_revoked_date,
                ]
                if d is not None
            ]
            auth_user.media_collection_acceptance_revoked_date = (
                max(media_collection_revoked_dates) if media_collection_revoked_dates else None
            )

            await self.session.flush()
            updated_user = auth_user

        elif anon_user is not None and auth_user is None:
            # Create new authenticated user with anonymous user's data
            created_user = User(
                client=auth_user_client,
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

        # Migrate messages from anonymous user to authenticated user
        updated_messages_count = await self.migrate_messages_to_new_user(
            previous_user_id=anonymous_user_id, new_user_id=auth_user_client
        )

        await self.session.commit()

        if updated_user is not None:
            await self.session.refresh(updated_user)

        return UserMigrationResponse.model_validate({
            "updated_user": updated_user,
            "messages_updated_count": updated_messages_count,
        })

    async def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str):
        """Migrate messages and labels from previous user to new user.

        Note: This method does NOT commit - the caller is responsible for committing.
        """
        await self.session.execute(update(Label).where(Label.creator == previous_user_id).values(creator=new_user_id))
        result = await self.session.execute(
            update(Message)
            .where(Message.creator == previous_user_id)
            .values(creator=new_user_id, expiration_time=None, private=False)
        )
        # cast is recommended by SQLAlchemy for this: https://github.com/sqlalchemy/sqlalchemy/issues/12913
        count = cast(CursorResult, result).rowcount
        await self.session.flush()

        return count


UserMigrationServiceDependency = Annotated[UserMigrationService, Depends()]
