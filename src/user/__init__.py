from flask import Blueprint, jsonify
from werkzeug import exceptions

from src import db
from src.auth.auth_service import authn, request_agent, set_auth_cookie
from src.auth.authenticated_client import AuthenticatedClient
from src.user.user_service import upsert_user


class UserBlueprint(Blueprint):
    dbc: db.Client

    def __init__(self, dbc: db.Client):
        super().__init__("user", __name__)
        self.dbc = dbc

        self.get("/whoami")(self.whoami)
        self.put("/user")(self.upsert_user)

    def whoami(self):
        agent = request_agent(self.dbc)
        if agent is None or agent.expired():
            raise exceptions.Unauthorized()

        user = self.dbc.user.get_by_client(agent.client)
        has_accepted_terms_and_conditions = (
            user is not None
            and user.terms_accepted_date is not None
            and user.acceptance_revoked_date is None
        )

        return set_auth_cookie(
            jsonify(
                AuthenticatedClient(
                    client=agent.client,
                    has_accepted_terms_and_conditions=has_accepted_terms_and_conditions,
                ).model_dump(by_alias=True)
            ),
            agent,
        )

    def upsert_user(self):
        agent = authn(self.dbc)

        user = upsert_user(self.dbc, client=agent.client)

        dump = user.model_dump(by_alias=True) if user is not None else None
        return jsonify(dump)
