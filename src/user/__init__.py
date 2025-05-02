from flask import Blueprint, jsonify, request
from flask_pydantic_api.api_wrapper import pydantic_api
from pydantic import ValidationError
from werkzeug import exceptions

from src import db
from src.auth.auth_service import authn, request_agent
from src.auth.auth_utils import get_permissions
from src.auth.authenticated_client import AuthenticatedClient
from src.auth.resource_protectors import (
    anonymous_auth_protector as anonymous_auth_protector,
)
from src.auth.resource_protectors import required_auth_protector
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.user.user_service import (
    MigrateFromAnonymousUserRequest,
    migrate_user_from_anonymous_user,
    upsert_user,
)


class UserBlueprint(Blueprint):
    dbc: db.Client
    storage_client: GoogleCloudStorage

    def __init__(self, dbc: db.Client, storage_client: GoogleCloudStorage):
        super().__init__("user", __name__)
        self.dbc = dbc
        self.storage_client = storage_client

        self.get("/whoami")(self.whoami)
        self.put("/user")(self.upsert_user)
        self.put(rule="/migrate-user")(self.migrate_from_anonymous_user)

    @pydantic_api(
        name="Get info for the current user",
        tags=["v3", "user"],
        model_dump_kwargs={"by_alias": True},
    )
    def whoami(self) -> AuthenticatedClient:
        agent = request_agent()
        if agent is None or agent.expired():
            raise exceptions.Unauthorized

        user = self.dbc.user.get_by_client(agent.client)
        has_accepted_terms_and_conditions = (
            user is not None
            and user.terms_accepted_date is not None
            and (user.acceptance_revoked_date is None or user.acceptance_revoked_date < user.terms_accepted_date)
        )

        return AuthenticatedClient(
            id=user.id if user is not None else None,
            client=agent.client,
            has_accepted_terms_and_conditions=has_accepted_terms_and_conditions,
            permissions=get_permissions(agent.token),
        )

    def upsert_user(self):
        agent = authn()

        user = upsert_user(self.dbc, client=agent.client)

        dump = user.model_dump(by_alias=True) if user is not None else None
        return jsonify(dump)

    def migrate_from_anonymous_user(self):
        with required_auth_protector.acquire() as token:
            if request.json is None:
                msg = "no request body"
                raise exceptions.BadRequest(msg)

            try:
                migration_request = MigrateFromAnonymousUserRequest.model_validate({
                    "anonymous_user_id": request.json["anonymous_user_id"],
                    "new_user_id": token.sub,
                })

                migration_result = migrate_user_from_anonymous_user(
                    dbc=self.dbc,
                    storage_client=self.storage_client,
                    anonymous_user_id=migration_request.anonymous_user_id,
                    new_user_id=migration_request.new_user_id,
                )

                return migration_result.model_dump_json()
            except ValidationError as e:
                raise exceptions.BadRequest(e.json()) from e
