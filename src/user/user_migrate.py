from typing import Annotated

from fastapi import Depends
from pydantic import Field
from sqlalchemy.orm import Session

from src import db
from src.api_interface import APIInterface
from src.dao.message.message_repository import MessageRepository
from src.dao.user import User
from src.dependencies import DBSession
from src.message.GoogleCloudStorage import GoogleCloudStorage


class MigrateFromAnonymousUserRequest(APIInterface):
    anonymous_user_id: str = Field()
    new_user_id: str = Field()


class MigrateFromAnonymousUserResponse(APIInterface):
    updated_user: User | None = Field()
    messages_updated_count: int = Field()


def migrate_user_from_anonymous_user(
    dbc: db.Client, storage_client: GoogleCloudStorage, session: Session, anonymous_user_id: str, new_user_id: str
):
    # migrate tos
    previous_user = dbc.user.get_by_client(anonymous_user_id)
    new_user = dbc.user.get_by_client(new_user_id)

    updated_user = None

    if previous_user is not None and new_user is not None:
        most_recent_terms_accepted_date = max(previous_user.terms_accepted_date, new_user.terms_accepted_date)
        most_recent_data_collection_accepted_date = max(
            (
                d
                for d in [previous_user.data_collection_accepted_date, new_user.data_collection_accepted_date]
                if d is not None
            ),
            default=None,
        )

        # TODO: carry over acceptance revoked date

        updated_user = dbc.user.update(
            client=new_user_id,
            terms_accepted_date=most_recent_terms_accepted_date,
            data_collection_accepted_date=most_recent_data_collection_accepted_date,
        )

    elif previous_user is not None and new_user is None:
        updated_user = dbc.user.create(
            client=new_user_id,
            terms_accepted_date=previous_user.terms_accepted_date,
            acceptance_revoked_date=previous_user.acceptance_revoked_date,
            data_collection_accepted_date=previous_user.data_collection_accepted_date,
            data_collection_acceptance_revoked_date=previous_user.data_collection_acceptance_revoked_date,
        )

    elif previous_user is None and new_user is not None:
        updated_user = new_user

    message_repository = MessageRepository(session)

    msgs_to_be_migrated = message_repository.get_by_creator(anonymous_user_id)

    for index, msg in enumerate(msgs_to_be_migrated):
        # 1. migrate anonyous files on Google Cloud
        for url in msg.file_urls or []:
            filename = url.split("/")[-1]
            whole_name = f"{msg.root}/{filename}"
            storage_client.migrate_anonymous_file(whole_name)

    updated_messages_count = message_repository.migrate_messages_to_new_user(
        previous_user_id=anonymous_user_id, new_user_id=new_user_id
    )

    return MigrateFromAnonymousUserResponse(
        updated_user=updated_user,
        messages_updated_count=updated_messages_count,
    )


# Service class with dependency injection
class UserMigrationService:
    """
    User migration service with dependency-injected database session.

    This service encapsulates user migration operations and receives
    its dependencies through constructor injection.
    """

    def __init__(self, session: Session):
        self.session = session

    def migrate_user_from_anonymous_user(
        self, dbc: db.Client, storage_client: GoogleCloudStorage, anonymous_user_id: str, new_user_id: str
    ):
        """Migrate user data from anonymous user to authenticated user"""
        # migrate tos
        previous_user = dbc.user.get_by_client(anonymous_user_id)
        new_user = dbc.user.get_by_client(new_user_id)

        updated_user = None

        if previous_user is not None and new_user is not None:
            most_recent_terms_accepted_date = max(previous_user.terms_accepted_date, new_user.terms_accepted_date)
            most_recent_data_collection_accepted_date = max(
                (
                    d
                    for d in [previous_user.data_collection_accepted_date, new_user.data_collection_accepted_date]
                    if d is not None
                ),
                default=None,
            )

            # TODO: carry over acceptance revoked date

            updated_user = dbc.user.update(
                client=new_user_id,
                terms_accepted_date=most_recent_terms_accepted_date,
                data_collection_accepted_date=most_recent_data_collection_accepted_date,
            )

        elif previous_user is not None and new_user is None:
            updated_user = dbc.user.create(
                client=new_user_id,
                terms_accepted_date=previous_user.terms_accepted_date,
                acceptance_revoked_date=previous_user.acceptance_revoked_date,
                data_collection_accepted_date=previous_user.data_collection_accepted_date,
                data_collection_acceptance_revoked_date=previous_user.data_collection_acceptance_revoked_date,
            )

        elif previous_user is None and new_user is not None:
            updated_user = new_user

        message_repository = MessageRepository(self.session)

        msgs_to_be_migrated = message_repository.get_by_creator(anonymous_user_id)

        for index, msg in enumerate(msgs_to_be_migrated):
            # 1. migrate anonyous files on Google Cloud
            for url in msg.file_urls or []:
                filename = url.split("/")[-1]
                whole_name = f"{msg.root}/{filename}"
                storage_client.migrate_anonymous_file(whole_name)

        updated_messages_count = message_repository.migrate_messages_to_new_user(
            previous_user_id=anonymous_user_id, new_user_id=new_user_id
        )

        return MigrateFromAnonymousUserResponse(
            updated_user=updated_user,
            messages_updated_count=updated_messages_count,
        )


def get_user_migration_service(session: DBSession) -> UserMigrationService:
    """Dependency provider for UserMigrationService"""
    return UserMigrationService(session)


# Type alias for dependency injection
UserMigrationServiceDep = Annotated[UserMigrationService, Depends(get_user_migration_service)]
