from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

import httpx
from authlib.oauth2 import OAuth2Error
from fastapi import Depends, Header, HTTPException, status

from api.config import settings
from api.logging.fastapi_logger import FastAPIStructLogger
from core.auth.token import Token
from core.auth.token_validator import Auth0JWTBearerTokenValidator
from core.auth.user_info import UserInfo

logger = FastAPIStructLogger()


@lru_cache
def get_bearer_token_validator() -> Auth0JWTBearerTokenValidator:
    return Auth0JWTBearerTokenValidator(
        domain=settings.AUTH_DOMAIN,
        audience=settings.AUTH_AUDIENCE,
    )


class AuthService:
    def __init__(
        self,
        authorization: str | None = Header(None, alias="Authorization"),
        anonymous_user_id: str | None = Header(None, alias="X-Anonymous-User-ID"),
    ):
        self.authorization = authorization
        self.anonymous_user_id = anonymous_user_id
        self.validator = get_bearer_token_validator()

    def _get_token_from_header(self) -> str | None:
        if not self.authorization:
            return None

        try:
            scheme, token = self.authorization.split(" ", maxsplit=1)
            return token if scheme.lower() == "bearer" else None
        except ValueError:
            return None

    def _validate_token(self, token_string: str) -> Token:
        """
        Validate and create Token

        Raises OAuth2Error if token is invalid
        """
        token_data = self.validator.authenticate_token(token_string)

        if token_data is None:
            raise OAuth2Error(error="invalid_token", description="Invalid token")

        return Token(
            client=token_data.sub,
            is_anonymous_user=False,
            created=datetime.fromtimestamp(token_data.iat, tz=UTC),
            expires=datetime.fromtimestamp(token_data.exp, tz=UTC),
            creator=token_data.iss,
            token=token_data,
        )

    def require_auth(self) -> Token:
        token_string = self._get_token_from_header()

        if not token_string:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        try:
            return self._validate_token(token_string)
        except OAuth2Error as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            ) from e

    def get_token(self) -> Token | None:
        """Validate and create Token, falling back to anonymous if header present"""
        token_string = self._get_token_from_header()

        if token_string:
            try:
                return self._validate_token(token_string)
            except OAuth2Error:
                # if invalid, check for anonymous
                pass

        if self.anonymous_user_id:
            return Token(
                client=self.anonymous_user_id,
                is_anonymous_user=True,
                token=self.anonymous_user_id,
            )

        return None

    def optional_auth(self) -> Token:
        token = self.get_token()
        if token is None or token.expired():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return token

    async def get_user_info(self) -> UserInfo | None:
        """
        Fetch user info from Auth0 using the authorization header.

        Returns:
            UserInfo object with email, first_name, and last_name, or None if request fails
        """
        if not self.authorization:
            return None

        headers = {"Authorization": self.authorization, "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://{settings.AUTH_DOMAIN}/userinfo",
                    headers=headers,
                )

                if response.status_code == status.HTTP_200_OK:
                    user_info_data = response.json()
                    email = user_info_data.get("email")
                    first_name = user_info_data.get("given_name")
                    last_name = user_info_data.get("family_name")

                    return UserInfo(email=email, first_name=first_name, last_name=last_name)

                logger.error(
                    "Error fetching user info",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return None  # noqa: TRY300

            except Exception as e:
                logger.exception("Exception while fetching user info", error=str(e))
                return None


AuthServiceDependency = Annotated[AuthService, Depends()]
