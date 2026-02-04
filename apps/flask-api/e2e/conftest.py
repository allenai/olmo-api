import os

import pytest
from dotenv import find_dotenv, load_dotenv


@pytest.fixture(scope="session", autouse=True)
def load_env():
    env_file = find_dotenv(".env")
    load_dotenv(env_file)

    environment = os.getenv("ENV", "test")
    designated_env_file = find_dotenv(f".env.{environment}")
    load_dotenv(designated_env_file)

    env_local_file = find_dotenv(".env.local")
    load_dotenv(env_local_file)

    designated_env_local_file = find_dotenv(f".env.{environment}.local")
    load_dotenv(designated_env_local_file)
