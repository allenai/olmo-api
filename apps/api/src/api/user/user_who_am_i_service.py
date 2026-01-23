from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from api.auth.permission_service import PermissionServiceDependency
from api.db.sqlalchemy_engine import SessionDependency
from core.auth.authenticated_client import AuthenticatedClient
from core.auth.token import Token
from db.models.user import User

# CONST for valid terms acceptance date
# This should be updated whenever the terms and conditions are updated
# so that we can check if the user has accepted the latest version
LAST_TERMS_UPDATE_DATE = datetime(2025, 12, 16, tzinfo=UTC)


class UserWhoAmIService:
    def __init__(self, session: SessionDependency, permission_service: PermissionServiceDependency):
        self.session = session
        self.permission_service = permission_service

    async def get_by_client(self, token: Token) -> AuthenticatedClient:
        stmt = select(User).where(User.client == token.client)
        result = await self.session.scalars(stmt)
        user = result.one_or_none()

        # A user is considered to have accepted the latest terms if:
        # - they exist,
        # - their acceptance date is set,
        # - and they accepted on or after the latest terms update,
        #   OR if they revoked before terms update. (see const LAST_TERMS_UPDATE_DATE)
        has_accepted_terms_and_conditions = not (
            user is None
            or user.terms_accepted_date is None
            or (
                user.terms_accepted_date < LAST_TERMS_UPDATE_DATE
                and (user.acceptance_revoked_date is None or user.acceptance_revoked_date < LAST_TERMS_UPDATE_DATE)
            )
        )

        has_accepted_data_collection = (
            user is not None
            and user.data_collection_accepted_date is not None
            and (
                user.data_collection_acceptance_revoked_date is None
                or user.data_collection_acceptance_revoked_date < user.data_collection_accepted_date
            )
        )

        has_accepted_media_collection = (
            user is not None
            and user.media_collection_accepted_date is not None
            and (
                user.media_collection_acceptance_revoked_date is None
                or user.media_collection_acceptance_revoked_date < user.media_collection_accepted_date
            )
        )

        permissions = self.permission_service.get_permissions(token)

        auth_client = AuthenticatedClient(
            id=user.id if user else None,
            client=user.client if user else token.client,
            has_accepted_terms_and_conditions=has_accepted_terms_and_conditions,
            has_accepted_data_collection=has_accepted_data_collection,
            has_accepted_media_collection=has_accepted_media_collection,
            permissions=permissions,
        )

        return auth_client


UserWhoAmIServiceDependency = Annotated[UserWhoAmIService, Depends()]
