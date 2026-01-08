from typing import cast

import requests
from flask import current_app

from core.auth.user_info import UserInfo
from src.auth.auth_service import get_user_info
from src.config.get_config import cfg

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


def create_contact():
    user_info = get_user_info()

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
        current_app.logger.info("Contact created successfully:", response.json())
    else:
        current_app.logger.error("Error creating contact:", response.status_code, response.text)
