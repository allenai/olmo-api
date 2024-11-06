import json
from urllib.request import urlopen

from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.integrations.flask_oauth2.requests import FlaskJsonRequest
from authlib.integrations.flask_oauth2.signals import token_authenticated
from authlib.jose.rfc7517.jwk import JsonWebKey
from authlib.oauth2 import OAuth2Error
from authlib.oauth2 import ResourceProtector as BaseResourceProtector
from authlib.oauth2.rfc6749 import (
    MissingAuthorizationError,
)
from authlib.oauth2.rfc7523 import JWTBearerTokenValidator
from flask import g
from flask import request as flask_request

from src.config import cfg

# Most code in this file is adapted from the Auth0 Python quickstart, found here: https://auth0.com/docs/quickstart/backend/python/interactive
# If that code changes, the files can be found on their commit here:
# https://github.com/auth0/docs/blob/62a8e6d544246a56b89a8ec87b3ceb8700b51261/articles/quickstart/backend/python/files/server.md
# https://github.com/auth0/docs/blob/62a8e6d544246a56b89a8ec87b3ceb8700b51261/articles/quickstart/backend/python/files/validator.md


class Auth0JWTBearerTokenValidator(JWTBearerTokenValidator):
    def __init__(self, domain: str, audience: str):
        issuer = f"https://{domain}/"
        jsonurl = urlopen(f"{issuer}.well-known/jwks.json")
        public_key = JsonWebKey.import_key_set(json.loads(jsonurl.read()))
        super(Auth0JWTBearerTokenValidator, self).__init__(public_key)
        self.claims_options = {
            "exp": {"essential": True},
            "aud": {"essential": True, "value": audience},
            "iss": {"essential": True, "value": issuer},
        }


validator = Auth0JWTBearerTokenValidator(
    domain=cfg.auth.domain, audience=cfg.auth.audience
)

require_auth = ResourceProtector()
require_auth.register_token_validator(validator)


class CustomResourceProtector(BaseResourceProtector):
    def acquire_token(self, scopes=None, **kwargs):
        """A method to acquire current valid token with the given scope.

        :param scopes: a list of scope values
        :return: token object
        """
        request = FlaskJsonRequest(flask_request)
        # backward compatibility
        kwargs["scopes"] = scopes
        for claim in kwargs:
            if isinstance(kwargs[claim], str):
                kwargs[claim] = [kwargs[claim]]
        token = self.validate_request(request=request, **kwargs)
        token_authenticated.send(self, token=token)
        g.authlib_server_oauth2_token = token
        return token

    def get_token(self, optional=False, **kwargs):
        claims = kwargs

        try:
            token = self.acquire_token(**claims)

            return token
        except MissingAuthorizationError:
            if optional:
                anonymous_user_id = flask_request.headers.get("X-Anonymous-User-ID")

                return anonymous_user_id

            return None
        except OAuth2Error:
            return None


maybe_auth = CustomResourceProtector()
maybe_auth.register_token_validator(validator)
