from enum import StrEnum
from typing import Any


class Permissions(StrEnum):
    READ_INTERNAL_MODELS = "read:internal-models"
    WRITE_MODEL_CONFIG = "write:model-config"
    BYPASS_SAFETY_CHECKS = "bypass-safety-checks"


def get_permissions(token: dict[str, Any] | str | None) -> list[Any] | Any:
    if not isinstance(token, dict):
        return []

    return token.get("permissions", [])


def user_has_permission(token: dict[str, Any] | str | None, permission: Permissions):
    permissions = get_permissions(token)

    return permission in permissions
