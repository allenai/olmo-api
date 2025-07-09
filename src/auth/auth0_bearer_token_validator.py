import json
import logging
from urllib.request import urlopen

from authlib.jose.rfc7517.jwk import JsonWebKey
from authlib.oauth2.rfc7523 import JWTBearerTokenValidator

logger = logging.getLogger(__name__)

OLD_AUTH0_ISSUER = "https://allenai-public.us.auth0.com/"

# Most code in this file is adapted from the Auth0 Python quickstart, found here: https://auth0.com/docs/quickstart/backend/python/interactive
# If that code changes, the files can be found on their commit here:
# https://github.com/auth0/docs/blob/62a8e6d544246a56b89a8ec87b3ceb8700b51261/articles/quickstart/backend/python/files/server.md
# https://github.com/auth0/docs/blob/62a8e6d544246a56b89a8ec87b3ceb8700b51261/articles/quickstart/backend/python/files/validator.md


class Auth0JWTBearerTokenValidator(JWTBearerTokenValidator):
    def __init__(self, domain: str, audience: str):
        issuer = f"https://{domain}/"
        jsonurl = urlopen(f"{issuer}.well-known/jwks.json")
        public_key = JsonWebKey.import_key_set(json.loads(jsonurl.read()))
        super().__init__(public_key)
        self.claims_options = {
            "exp": {"essential": True},
            "aud": {"essential": True, "value": audience},
            "iss": {"essential": True, "values": [issuer, OLD_AUTH0_ISSUER]},
        }
