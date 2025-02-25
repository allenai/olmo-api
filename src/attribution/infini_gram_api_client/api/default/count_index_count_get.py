from http import HTTPStatus
from typing import Any

import httpx

from src.attribution.infini_gram_api_client import errors
from src.attribution.infini_gram_api_client.client import AuthenticatedClient, Client
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from src.attribution.infini_gram_api_client.models.http_validation_error import HTTPValidationError
from src.attribution.infini_gram_api_client.models.infini_gram_count_response import InfiniGramCountResponse
from src.attribution.infini_gram_api_client.types import UNSET, Response


def _get_kwargs(
    index: AvailableInfiniGramIndexId,
    *,
    query: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["query"] = query

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/{index}/count",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | InfiniGramCountResponse | None:
    if response.status_code == 200:
        return InfiniGramCountResponse.from_dict(response.json())

    if response.status_code == 422:
        return HTTPValidationError.from_dict(response.json())

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | InfiniGramCountResponse]:
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
    query: str,
) -> Response[HTTPValidationError | InfiniGramCountResponse]:
    """Count

    Args:
        index (AvailableInfiniGramIndexId):
        query (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, InfiniGramCountResponse]]
    """

    kwargs = _get_kwargs(
        index=index,
        query=query,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    index: AvailableInfiniGramIndexId,
    *,
    client: AuthenticatedClient | Client,
    query: str,
) -> HTTPValidationError | InfiniGramCountResponse | None:
    """Count

    Args:
        index (AvailableInfiniGramIndexId):
        query (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, InfiniGramCountResponse]
    """

    return sync_detailed(
        index=index,
        client=client,
        query=query,
    ).parsed


async def asyncio_detailed(
    index: AvailableInfiniGramIndexId,
    *,
    client: AuthenticatedClient | Client,
    query: str,
) -> Response[HTTPValidationError | InfiniGramCountResponse]:
    """Count

    Args:
        index (AvailableInfiniGramIndexId):
        query (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, InfiniGramCountResponse]]
    """

    kwargs = _get_kwargs(
        index=index,
        query=query,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    index: AvailableInfiniGramIndexId,
    *,
    client: AuthenticatedClient | Client,
    query: str,
) -> HTTPValidationError | InfiniGramCountResponse | None:
    """Count

    Args:
        index (AvailableInfiniGramIndexId):
        query (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, InfiniGramCountResponse]
    """

    return (
        await asyncio_detailed(
            index=index,
            client=client,
            query=query,
        )
    ).parsed
