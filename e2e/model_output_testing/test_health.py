import pytest


@pytest.mark.production
def test_health_endpoint(production_base_url, http):
    """Basic smoke test for the production API."""
    candidates = ["/health"]
    for path in candidates:
        url = production_base_url + path
        resp = http.get(url, timeout=10)
        if resp.status_code == 204:
            # success
            return
    pytest.fail(f"Endpoints did not return 204: tried {candidates}")
