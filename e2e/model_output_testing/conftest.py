import os
from collections.abc import Generator

import pytest
import requests


def pytest_configure(config):
    # register marker for clarity
    config.addinivalue_line("markers", "production: mark production end-to-end tests")


@pytest.fixture(scope="session")
def production_base_url():
    """Return the production API base URL from the environment.

    Tests will be skipped at collection time if this is not set to avoid
    accidentally hitting production when running the default localhost suite.
    """
    url = os.environ.get("PRODUCTION_API_BASE")
    if not url:
        pytest.skip("PRODUCTION_API_BASE not set; skipping production tests")
    # Basic validation
    if not url.startswith("http://") and not url.startswith("https://"):
        msg = "PRODUCTION_API_BASE must start with http:// or https://"
        raise ValueError(msg)
    return url.rstrip("/")


@pytest.fixture
def http() -> Generator[requests.Session, None, None]:
    """Provide a simple requests session for tests."""
    s = requests.Session()
    try:
        yield s
    finally:
        s.close()
