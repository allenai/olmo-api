from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, status

from api.auth.auth_service import AuthServiceDependency
from core.auth.token import Token


class Permissions(StrEnum):
    READ_INTERNAL_MODELS = "read:internal-models"
    WRITE_MODEL_CONFIG = "write:model-config"
    WRITE_BYPASS_SAFETY_CHECKS = "write:bypass-safety-check"


class PermissionService:
    def __init__(self, auth_service: AuthServiceDependency):
        self.auth_service = auth_service

    @classmethod
    def get_permissions(cls, token: Token | None) -> list[str]:
        if token is None or token.is_anonymous_user:
            return []

        if not isinstance(token.token, dict):
            return []

        return token.token.get("permissions", [])

    def has_permission(self, token: Token | None, permission: Permissions) -> bool:
        permissions = self.get_permissions(token)
        return permission in permissions

    def require_permission(self, permission: Permissions) -> Token:
        token = self.auth_service.require_auth()

        if not self.has_permission(token, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )

        return token


PermissionServiceDependency = Annotated[PermissionService, Depends()]
