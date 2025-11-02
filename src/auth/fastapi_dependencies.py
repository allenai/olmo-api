"""
FastAPI Authentication Dependencies
------------------------------------

Provides FastAPI dependencies for authentication and authorization,
replacing Flask's resource protectors with FastAPI's dependency injection system.

Uses PyJWT for JWT validation instead of Authlib.
"""

from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from src.auth.token import Token
from src.constants import ANONYMOUS_USER_ID_HEADER
from src.dependencies import AppConfig

# HTTPBearer security scheme (auto_error=False means it won't raise 401 automatically)
security = HTTPBearer(auto_error=False)

# Old Auth0 issuer for backward compatibility
OLD_AUTH0_ISSUER = "https://allenai-public.us.auth0.com/"


@lru_cache
def get_jwks_client(domain: str) -> PyJWKClient:
    """
    Get PyJWKClient for fetching JWKS (JSON Web Key Set).

    Cached singleton to avoid repeated JWKS fetches.
    """
    issuer = f"https://{domain}/"
    jwks_url = f"{issuer}.well-known/jwks.json"
    return PyJWKClient(jwks_url)


def get_optional_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    anonymous_user_id: Optional[str] = Header(None, alias=ANONYMOUS_USER_ID_HEADER),
    config: AppConfig = None,
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
        # Try to validate JWT token using PyJWT
        try:
            token_string = credentials.credentials

            # Get JWKS client for token verification
            jwks_client = get_jwks_client(config.auth.domain)

            # Get signing key from token header
            signing_key = jwks_client.get_signing_key_from_jwt(token_string)

            # Decode and validate token
            issuer = f"https://{config.auth.domain}/"

            # Note: PyJWT doesn't support multiple issuers in jwt.decode()
            # We'll verify issuer manually after decoding
            token_data = jwt.decode(
                token_string,
                signing_key.key,
                algorithms=["RS256"],
                audience=config.auth.audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": False,  # We'll verify manually below
                }
            )

            # Manually verify issuer supports both old and new domains
            if token_data.get("iss") not in [issuer, OLD_AUTH0_ISSUER]:
                raise jwt.InvalidIssuerError(f"Invalid issuer: {token_data.get('iss')}")

            # Successfully authenticated with Auth0
            return Token(
                client=token_data["sub"],
                is_anonymous_user=False,
                created=datetime.fromtimestamp(token_data["iat"], tz=UTC),
                expires=datetime.fromtimestamp(token_data["exp"], tz=UTC),
                creator=token_data["iss"],
                token=token_data,
            )
        except (jwt.PyJWTError, KeyError):
            # Invalid token or missing required claims, fall through to check anonymous
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
