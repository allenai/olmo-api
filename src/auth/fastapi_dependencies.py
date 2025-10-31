"""
FastAPI Authentication Dependencies
------------------------------------

Provides FastAPI dependencies for authentication and authorization,
replacing Flask's resource protectors with FastAPI's dependency injection system.
"""

from datetime import UTC, datetime
from typing import Annotated, Optional

from authlib.oauth2 import OAuth2Error
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.auth0_bearer_token_validator import Auth0JWTBearerTokenValidator
from src.auth.token import Token
from src.config.get_config import cfg
from src.constants import ANONYMOUS_USER_ID_HEADER

# HTTPBearer security scheme (auto_error=False means it won't raise 401 automatically)
security = HTTPBearer(auto_error=False)


def get_auth0_validator(request: Request) -> Auth0JWTBearerTokenValidator:
    """
    Get Auth0 validator from app state or create new one.

    The validator is cached in app state to avoid fetching JWKS repeatedly.
    """
    if not hasattr(request.app.state, "auth0_validator"):
        request.app.state.auth0_validator = Auth0JWTBearerTokenValidator(
            domain=cfg.auth.domain, audience=cfg.auth.audience
        )
    return request.app.state.auth0_validator


def get_optional_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    anonymous_user_id: Optional[str] = Header(None, alias=ANONYMOUS_USER_ID_HEADER),
    validator: Auth0JWTBearerTokenValidator = Depends(get_auth0_validator),
) -> Optional[Token]:
    """
    Get token from Authorization header or anonymous user header.

    This dependency replaces the Flask anonymous_auth_protector.get_token() pattern.
    It supports three authentication modes:
    1. JWT Bearer token (Auth0 authenticated user)
    2. Anonymous user ID header
    3. No authentication (returns None)

    Returns:
        Token object if authenticated (either way), None if no credentials provided
    """
    if credentials:
        # Try to validate JWT token
        try:
            token_string = credentials.credentials
            token_data = validator.authenticate_token(token_string, request=None, scopes=None)

            if token_data:
                # Successfully authenticated with Auth0
                return Token(
                    client=token_data.sub,
                    is_anonymous_user=False,
                    created=datetime.fromtimestamp(token_data.iat, tz=UTC),
                    expires=datetime.fromtimestamp(token_data.exp, tz=UTC),
                    creator=token_data.iss,
                    token=token_data,
                )
        except OAuth2Error:
            # Invalid token, fall through to check anonymous
            pass

    if anonymous_user_id:
        # Anonymous user authentication
        return Token(
            client=anonymous_user_id,
            is_anonymous_user=True,
            created=None,
            expires=None,
            creator="anonymous",
            token=anonymous_user_id,
        )

    return None


def require_token(token: Optional[Token] = Depends(get_optional_token)) -> Token:
    """
    Require authentication - raises 401 if no valid token.

    This dependency replaces the Flask authn() function.

    Usage:
        @router.get("/protected")
        async def protected_endpoint(token: RequiredAuth):
            # token is guaranteed to be non-None here
            pass
    """
    if token is None or token.expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def require_token_with_scope(scope: str):
    """
    Dependency factory for scope-based authorization.

    This replaces the Flask required_auth_protector(scope) decorator pattern.

    Usage:
        @router.post("/admin/models", dependencies=[Depends(require_token_with_scope("write:model-config"))])
        async def create_model(...):
            pass

    Or for per-endpoint:
        @router.post("/admin/models")
        async def create_model(
            token: Annotated[Token, Depends(require_token_with_scope("write:model-config"))]
        ):
            pass
    """

    def check_scope(token: Token = Depends(require_token)) -> Token:
        # Check if token has the required scope
        if isinstance(token.token, dict) or hasattr(token.token, "get"):
            permissions = token.token.get("permissions", [])
        else:
            permissions = []

        if scope not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Insufficient permissions: {scope} required"
            )
        return token

    return check_scope


# Type aliases for dependency injection
# These make it easy to inject auth in route handlers
OptionalAuth = Annotated[Optional[Token], Depends(get_optional_token)]
RequiredAuth = Annotated[Token, Depends(require_token)]
