from pydantic import Field

from api.config import Settings


# Inherit settings from API -- add additional test related settings
class TestSettings(Settings):
    E2E_AUTH0_CLIENT_ID: str = Field(init=False)
    E2E_AUTH0_CLIENT_SECRET: str = Field(init=False)


settings = TestSettings()
