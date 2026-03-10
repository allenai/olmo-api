from typing import Annotated

from fastapi import Depends

from api.auth.auth_service import AuthServiceDependency
from core.auth import Token


def get_optional_auth_user(auth_service: AuthServiceDependency) -> Token:
    return auth_service.optional_auth()


OptionalAuthUser = Annotated[Token, Depends(get_optional_auth_user)]
