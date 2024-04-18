from flask import Blueprint, jsonify
from werkzeug import exceptions

from src import db
from src.auth.auth_service import request_agent, set_auth_cookie
from src.auth.authenticated_client import AuthenticatedClient


class UserBlueprint(Blueprint):
    dbc: db.Client

    def __init__(self, dbc: db.Client):
        super().__init__("user", __name__)
        self.dbc = dbc

        self.get("/whoami")(self.whoami)

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
                )
            ),
            agent,
        )
