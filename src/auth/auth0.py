import json
from urllib.request import urlopen

from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.jose.rfc7517.jwk import JsonWebKey
from authlib.oauth2.rfc7523 import JWTBearerTokenValidator

from src.auth.allow_anonymous_resource_provider import AllowAnonymousResourceProtector
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


maybe_auth = AllowAnonymousResourceProtector()
maybe_auth.register_token_validator(validator)
