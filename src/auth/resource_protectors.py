from authlib.integrations.flask_oauth2 import ResourceProtector

from src.auth.allow_anonymous_resource_provider import AllowAnonymousResourceProtector
from src.auth.auth0_bearer_token_validator import Auth0JWTBearerTokenValidator
from src.config import cfg

validator = Auth0JWTBearerTokenValidator(
    domain=cfg.auth.domain, audience=cfg.auth.audience
)

required_auth_protector = ResourceProtector()
required_auth_protector.register_token_validator(validator)


# this DOES NOT handle missing scopes properly
# if we add an admin page we'll need to make sure we use the provider that requires a login
anonymous_auth_protector = AllowAnonymousResourceProtector()
anonymous_auth_protector.register_token_validator(validator)
