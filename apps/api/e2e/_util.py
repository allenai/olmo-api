from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import Response


def assert_ok_response(response: Response):
    assert response.status_code == HTTPStatus.OK, f"{response.url} responded with an non-success: {response.text}"
