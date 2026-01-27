from typing import Annotated, cast

import httpx
from fastapi import Depends, status

from api.auth.auth_service import AuthServiceDependency
from api.config import settings
from api.logging.fastapi_logger import FastAPIStructLogger
from core.auth.user_info import UserInfo

HUBSPOT_URL = "https://api.hubapi.com"

logger = FastAPIStructLogger()


class HubSpotService:
    """Service for creating HubSpot contacts."""

    def __init__(self, auth_service: AuthServiceDependency):
        self.hubspot_url = HUBSPOT_URL
        self.hubspot_token = settings.HUBSPOT_TOKEN
        self.auth_service = auth_service

    async def check_contact_exists(self, user_info: UserInfo | None) -> bool:
        """
        Check if a HubSpot contact exists for the given user.

        Args:
            user_info: User information containing email to search for

        Returns:
            True if contact exists, False otherwise
        """
        if user_info is None:
            return False

        if not self.hubspot_token:
            logger.warning("HubSpot token not configured, skipping contact check")
            return False

        url = f"{self.hubspot_url}/crm/v3/objects/contacts/search"
        headers = {
            "Authorization": f"Bearer {self.hubspot_token}",
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

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=data)

                if response.status_code == status.HTTP_200_OK:
                    response_data = response.json()
                    return len(cast(list, response_data.get("results", []))) > 0
                return False  # noqa: TRY300

            except Exception as e:
                logger.exception("Exception while checking HubSpot contact", error=str(e))
                return False

    async def create_contact(self) -> None:
        """
        Create a HubSpot contact for the authenticated user.

        Returns:
            None
        """
        if not self.hubspot_token:
            logger.warning("HubSpot token not configured, skipping contact creation")
            return

        user_info = await self.auth_service.get_user_info()

        if user_info is None:
            return

        if await self.check_contact_exists(user_info):
            return

        url = f"{self.hubspot_url}/crm/v3/objects/contacts"
        headers = {
            "Authorization": f"Bearer {self.hubspot_token}",
            "Content-Type": "application/json",
        }

        contact_data = {
            "properties": {
                "email": user_info.email,
                "firstname": user_info.first_name,
                "lastname": user_info.last_name,
                "created_by_playground_app": "true",
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=contact_data)

                if response.status_code == status.HTTP_201_CREATED:
                    logger.info("Contact created successfully", response=response.json())
                else:
                    logger.error(
                        "Error while creating HubSpot contact",
                        status_code=response.status_code,
                        response_text=response.text,
                    )

            except Exception as e:
                logger.exception("Exception while creating HubSpot contact", error=str(e))


HubSpotServiceDependency = Annotated[HubSpotService, Depends()]
