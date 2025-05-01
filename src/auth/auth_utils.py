from typing import Any


def get_permissions(token: dict[str, Any] | str | None) -> list[Any] | Any:
    if not isinstance(token, dict):
        return []

    return token.get("permissions", [])


def user_has_permission(token: dict[str, Any] | str | None, permission: str):
    permissions = get_permissions(token)

    return permission in permissions
