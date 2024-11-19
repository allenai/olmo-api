from typing import Optional

from flask import Blueprint, jsonify, request
from pydantic import BaseModel, Field, ValidationError
from werkzeug import exceptions

from src import db
from src.api_interface import APIInterface
from src.auth.auth_service import authn, request_agent
from src.auth.authenticated_client import AuthenticatedClient
from src.auth.resource_protectors import required_auth_protector
from src.dao.user import User
from src.user.user_service import (
    MigrateFromAnonymousUserRequest,
    migrate_user_from_anonymous_user,
    upsert_user,
)


class UserBlueprint(Blueprint):
    dbc: db.Client

    def __init__(self, dbc: db.Client):
        super().__init__("user", __name__)
        self.dbc = dbc

        self.get("/whoami")(self.whoami)
        self.put("/user")(self.upsert_user)
        self.put(rule="/migrate-user")(self.migrate_from_anonymous_user)

    def whoami(self):
        agent = request_agent()
        if agent is None or agent.expired():
            raise exceptions.Unauthorized()

        user = self.dbc.user.get_by_client(agent.client)
        has_accepted_terms_and_conditions = (
            user is not None
            and user.terms_accepted_date is not None
            and (
                user.acceptance_revoked_date is None
                or user.acceptance_revoked_date < user.terms_accepted_date
            )
        )

        return jsonify(
            AuthenticatedClient(
                id=user.id if user is not None else None,
                client=agent.client,
                has_accepted_terms_and_conditions=has_accepted_terms_and_conditions,
            ).model_dump(by_alias=True)
        )

    def upsert_user(self):
        agent = authn()

        user = upsert_user(self.dbc, client=agent.client)

        dump = user.model_dump(by_alias=True) if user is not None else None
        return jsonify(dump)

    def migrate_from_anonymous_user(self):
        with required_auth_protector.acquire() as token:
            if request.json is None:
                raise exceptions.BadRequest("no request body")

            try:
                migration_request = MigrateFromAnonymousUserRequest.model_validate(
                    {
                        "anonymous_user_id": request.json["anonymous_user_id"],
                        "new_user_id": token.sub,
                    }
                )

                migration_result = migrate_user_from_anonymous_user(
                    dbc=self.dbc,
                    anonymous_user_id=migration_request.anonymous_user_id,
                    new_user_id=migration_request.new_user_id,
                )

                return migration_result.model_dump_json()
            except ValidationError as e:
                raise exceptions.BadRequest(e.json())
