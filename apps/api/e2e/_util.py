from http import HTTPStatus

from httpx import Response


def assert_ok_response(response: Response):
    assert response.status_code == HTTPStatus.OK, (  # noqa: S101
        f"{response.url} responded with an non-success: {response.text}"
    )
