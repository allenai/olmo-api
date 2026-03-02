from http import HTTPStatus

from httpx import Response


def assert_ok_response(response: Response):
    assert response.status_code == HTTPStatus.OK, f"{response.url} responded with an non-success: {response.text}"
