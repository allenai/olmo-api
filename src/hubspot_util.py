from dataclasses import dataclass
from typing import Optional
from src.config import cfg

from flask import request, current_app

import requests

HUBSPOT_URL = 'https://api.hubapi.com'

@dataclass
class UserInfo:
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

def get_user_info() -> Optional[UserInfo]:
    auth = request.headers.get("Authorization")
    headers = {
            "Authorization": f"{auth}",
            "Content-Type": "application/json"
        }
    response = requests.get(f'https://{cfg.auth.domain}/userinfo', headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        email = user_info.get('email')
        first_name = user_info.get('given_name')
        last_name = user_info.get('family_name')

        return UserInfo(email=email, first_name=first_name, last_name=last_name)
    else:
        current_app.logger.error('Error fetching user info:', response.status_code, response.text)
        return None  
    
def contact_exists(user_info: Optional[UserInfo]):
    url = f"{HUBSPOT_URL}/crm/v3/objects/contacts/search"

    if user_info is None: 
        return

    headers = {
        "Authorization": f"Bearer {cfg.hubspot.token}",
        "Content-Type": "application/json"
    }
    data = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "email",
                "operator": "EQ",
                "value": user_info.email,
            }]
        }],
        "limit": 1
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        data = response.json()
        return len(data.get('results', [])) > 0
    return False
    
def create_contact():
    user_info = get_user_info()

    if contact_exists(user_info):
        return
           
    url = f"{HUBSPOT_URL}/crm/v3/objects/contacts"
    headers = {
        "Authorization": f"Bearer {cfg.hubspot.token}",
        "Content-Type": "application/json"
    }
    if user_info is None:
        return
    
    contact_data = {
        "properties": {
            "email": user_info.email, 
            "firstname": user_info.first_name,
            "lastname": user_info.last_name
        }
    }

    response = requests.post(url, headers=headers, json=contact_data)

    if response.status_code == 201:
        current_app.logger.info("Contact created successfully:", response.json())
    else:
        current_app.logger.error("Error creating contact:", response.status_code, response.text)