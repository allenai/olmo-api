from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.attribution_request import AttributionRequest
from ...models.attribution_response import AttributionResponse
from ...models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    index: AvailableInfiniGramIndexId,
    *,
    body: AttributionRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/{index}/attribution",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AttributionResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = AttributionResponse.from_dict(response.json())

        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[AttributionResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    index: AvailableInfiniGramIndexId,
    *,
    client: AuthenticatedClient | Client,
    body: AttributionRequest,
) -> Response[AttributionResponse | HTTPValidationError]:
    """Get Document Attributions

    Args:
        index (AvailableInfiniGramIndexId):
        body (AttributionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[AttributionResponse, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        index=index,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    index: AvailableInfiniGramIndexId,
    *,
    client: AuthenticatedClient | Client,
    body: AttributionRequest,
) -> AttributionResponse | HTTPValidationError | None:
    """Get Document Attributions

    Args:
        index (AvailableInfiniGramIndexId):
        body (AttributionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[AttributionResponse, HTTPValidationError]
    """

    return sync_detailed(
        index=index,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    index: AvailableInfiniGramIndexId,
    *,
    client: AuthenticatedClient | Client,
    body: AttributionRequest,
) -> Response[AttributionResponse | HTTPValidationError]:
    """Get Document Attributions

    Args:
        index (AvailableInfiniGramIndexId):
        body (AttributionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[AttributionResponse, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        index=index,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    index: AvailableInfiniGramIndexId,
    *,
    client: AuthenticatedClient | Client,
    body: AttributionRequest,
) -> AttributionResponse | HTTPValidationError | None:
    """Get Document Attributions

    Args:
        index (AvailableInfiniGramIndexId):
        body (AttributionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[AttributionResponse, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            index=index,
            client=client,
            body=body,
        )
    ).parsed
