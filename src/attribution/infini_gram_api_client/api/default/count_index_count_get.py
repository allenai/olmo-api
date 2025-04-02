from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from ...models.infini_gram_count_response import InfiniGramCountResponse
from ...models.request_validation_error import RequestValidationError
from ...types import UNSET, Response


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
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[InfiniGramCountResponse, RequestValidationError]]:
    if response.status_code == 200:
        response_200 = InfiniGramCountResponse.from_dict(response.json())

        return response_200
    if response.status_code == 422:
        response_422 = RequestValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[InfiniGramCountResponse, RequestValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    index: AvailableInfiniGramIndexId,
    *,
    client: Union[AuthenticatedClient, Client],
    query: str,
) -> Response[Union[InfiniGramCountResponse, RequestValidationError]]:
    """Count

    Args:
        index (AvailableInfiniGramIndexId):
        query (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[InfiniGramCountResponse, RequestValidationError]]
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
    client: Union[AuthenticatedClient, Client],
    query: str,
) -> Optional[Union[InfiniGramCountResponse, RequestValidationError]]:
    """Count

    Args:
        index (AvailableInfiniGramIndexId):
        query (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[InfiniGramCountResponse, RequestValidationError]
    """

    return sync_detailed(
        index=index,
        client=client,
        query=query,
    ).parsed


async def asyncio_detailed(
    index: AvailableInfiniGramIndexId,
    *,
    client: Union[AuthenticatedClient, Client],
    query: str,
) -> Response[Union[InfiniGramCountResponse, RequestValidationError]]:
    """Count

    Args:
        index (AvailableInfiniGramIndexId):
        query (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[InfiniGramCountResponse, RequestValidationError]]
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
    client: Union[AuthenticatedClient, Client],
    query: str,
) -> Optional[Union[InfiniGramCountResponse, RequestValidationError]]:
    """Count

    Args:
        index (AvailableInfiniGramIndexId):
        query (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[InfiniGramCountResponse, RequestValidationError]
    """

    return (
        await asyncio_detailed(
            index=index,
            client=client,
            query=query,
        )
    ).parsed
