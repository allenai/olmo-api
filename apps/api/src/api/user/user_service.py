from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi_problem.error import ConflictProblem
from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.db.sqlalchemy_engine import SessionDependency
from api.user.hubspot_service import HubSpotServiceDependency
from core.api_interface import APIInterface
from core.auth.token import Token
from db.models.user import User


class UpsertUserRequest(APIInterface):
    id: str | None = None
    terms_accepted_date: datetime | None = None
    acceptance_revoked_date: datetime | None = None
    data_collection_accepted_date: datetime | None = None
    data_collection_acceptance_revoked_date: datetime | None = None
    media_collection_accepted_date: datetime | None = None
    media_collection_acceptance_revoked_date: datetime | None = None


class UpsertUserResponse(APIInterface):
    id: str
    client: str
    terms_accepted_date: datetime | None = None
    acceptance_revoked_date: datetime | None = None
    data_collection_accepted_date: datetime | None = None
    data_collection_acceptance_revoked_date: datetime | None = None
    media_collection_accepted_date: datetime | None = None
    media_collection_acceptance_revoked_date: datetime | None = None


class UserService:
    def __init__(
        self,
        session: SessionDependency,
        hubspot_service: HubSpotServiceDependency,
    ):
        self.session = session
        self.hubspot_service = hubspot_service

    @staticmethod
    def _update_user(user_to_update: User, request: UpsertUserRequest) -> User:
        if request.id is not None:
            user_to_update.id = request.id
        if request.terms_accepted_date is not None:
            user_to_update.terms_accepted_date = request.terms_accepted_date
        if request.acceptance_revoked_date is not None:
            user_to_update.acceptance_revoked_date = request.acceptance_revoked_date
        if request.data_collection_accepted_date is not None:
            user_to_update.data_collection_accepted_date = request.data_collection_accepted_date
        if request.data_collection_acceptance_revoked_date is not None:
            user_to_update.data_collection_acceptance_revoked_date = request.data_collection_acceptance_revoked_date
        if request.media_collection_accepted_date is not None:
            user_to_update.media_collection_accepted_date = request.media_collection_accepted_date
        if request.media_collection_acceptance_revoked_date is not None:
            user_to_update.media_collection_acceptance_revoked_date = request.media_collection_acceptance_revoked_date

        return user_to_update

    async def upsert_user(
        self,
        request: UpsertUserRequest,
        token: Token,
    ) -> UpsertUserResponse:
        stmt = select(User).where(User.client == token.client)
        result = await self.session.scalars(stmt)
        user_to_update = result.one_or_none()

        if user_to_update is not None:
            self._update_user(user_to_update=user_to_update, request=request)

            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(user_to_update)

            return UpsertUserResponse.model_validate(user_to_update)

        new_user = User(
            client=token.client,
            terms_accepted_date=request.terms_accepted_date or datetime.now().astimezone(UTC),
            acceptance_revoked_date=request.acceptance_revoked_date,
            data_collection_accepted_date=request.data_collection_accepted_date,
            data_collection_acceptance_revoked_date=request.data_collection_acceptance_revoked_date,
            media_collection_accepted_date=request.media_collection_accepted_date,
            media_collection_acceptance_revoked_date=request.media_collection_acceptance_revoked_date,
        )

        self.session.add(new_user)
        try:
            await self.session.flush()
            await self.session.commit()
        except IntegrityError as e:
            if not isinstance(e.orig, UniqueViolation):
                raise

            # try again
            await self.session.rollback()
            result = await self.session.scalars(stmt)
            user_to_update = result.one()

            self._update_user(user_to_update=user_to_update, request=request)

            try:
                await self.session.flush()
                await self.session.commit()
            # Fail if it happens again
            except IntegrityError as e:
                if isinstance(e.orig, UniqueViolation):
                    raise ConflictProblem(detail="User already exists") from e
                raise

            return UpsertUserResponse.model_validate(user_to_update)

        await self.session.refresh(new_user)

        # Create HubSpot contact for new non-anonymous users
        should_create_contact = not token.is_anonymous_user
        if should_create_contact and new_user:
            await self.hubspot_service.create_contact()

        return UpsertUserResponse.model_validate(new_user)


UserServiceDependency = Annotated[UserService, Depends()]
