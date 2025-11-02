import structlog
from dataclasses import dataclass
from http import HTTPStatus
from typing import cast

import requests

from src.config.get_config import cfg

logger = structlog.get_logger(__name__)


@dataclass
class UserInfo:
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None

HUBSPOT_URL = "https://api.hubapi.com"


def get_contact(user_info: UserInfo | None):
    url = f"{HUBSPOT_URL}/crm/v3/objects/contacts/search"

    if user_info is None:
        return

    headers = {
        "Authorization": f"Bearer {cfg.hubspot.token}",
        "Content-Type": "application/json",
    }
    data = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": user_info.email,
                    }
                ]
            }
        ],
        "limit": 1,
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        data = response.json()
        return len(cast(list, data.get("results", []))) > 0
    return False


def get_user_info(auth_header: str) -> UserInfo | None:
    """Get user info from Auth0 using the Authorization header"""
    headers = {"Authorization": auth_header, "Content-Type": "application/json"}
    response = requests.get(f"https://{cfg.auth.domain}/userinfo", headers=headers)

    if response.status_code == HTTPStatus.OK:
        user_info = response.json()
        email = user_info.get("email")
        first_name = user_info.get("given_name")
        last_name = user_info.get("family_name")

        return UserInfo(email=email, first_name=first_name, last_name=last_name)
    logger.error("error_fetching_user_info", status_code=response.status_code, response_text=response.text)
    return None


def create_contact(auth_header: str):
    user_info = get_user_info(auth_header)

    if get_contact(user_info):
        return

    url = f"{HUBSPOT_URL}/crm/v3/objects/contacts"
    headers = {
        "Authorization": f"Bearer {cfg.hubspot.token}",
        "Content-Type": "application/json",
    }
    if user_info is None:
        return

    contact_data = {
        "properties": {
            "email": user_info.email,
            "firstname": user_info.first_name,
            "lastname": user_info.last_name,
            "created_by_playground_app": "true",
        }
    }

    response = requests.post(url, headers=headers, json=contact_data)

    if response.status_code == 201:
        logger.info("contact_created_successfully", response_data=response.json())
    else:
        logger.error("error_creating_contact", status_code=response.status_code, response_text=response.text)
