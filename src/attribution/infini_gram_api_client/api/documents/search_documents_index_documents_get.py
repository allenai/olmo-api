from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from ...models.http_validation_error import HTTPValidationError
from ...models.search_response import SearchResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    index: AvailableInfiniGramIndexId,
    *,
    search: str,
    maximum_document_display_length: Union[Unset, int] = 10,
    page: Union[Unset, int] = 0,
    page_size: Union[Unset, int] = 10,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["search"] = search

    params["maximum_document_display_length"] = maximum_document_display_length

    params["page"] = page

    params["page_size"] = page_size

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/{index}/documents/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, SearchResponse]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = SearchResponse.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[HTTPValidationError, SearchResponse]]:
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
    search: str,
    maximum_document_display_length: Union[Unset, int] = 10,
    page: Union[Unset, int] = 0,
    page_size: Union[Unset, int] = 10,
) -> Response[Union[HTTPValidationError, SearchResponse]]:
    """Search Documents

    Args:
        index (AvailableInfiniGramIndexId):
        search (str):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.
        page (Union[Unset, int]):  Default: 0.
        page_size (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, SearchResponse]]
    """

    kwargs = _get_kwargs(
        index=index,
        search=search,
        maximum_document_display_length=maximum_document_display_length,
        page=page,
        page_size=page_size,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    index: AvailableInfiniGramIndexId,
    *,
    client: Union[AuthenticatedClient, Client],
    search: str,
    maximum_document_display_length: Union[Unset, int] = 10,
    page: Union[Unset, int] = 0,
    page_size: Union[Unset, int] = 10,
) -> Optional[Union[HTTPValidationError, SearchResponse]]:
    """Search Documents

    Args:
        index (AvailableInfiniGramIndexId):
        search (str):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.
        page (Union[Unset, int]):  Default: 0.
        page_size (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, SearchResponse]
    """

    return sync_detailed(
        index=index,
        client=client,
        search=search,
        maximum_document_display_length=maximum_document_display_length,
        page=page,
        page_size=page_size,
    ).parsed


async def asyncio_detailed(
    index: AvailableInfiniGramIndexId,
    *,
    client: Union[AuthenticatedClient, Client],
    search: str,
    maximum_document_display_length: Union[Unset, int] = 10,
    page: Union[Unset, int] = 0,
    page_size: Union[Unset, int] = 10,
) -> Response[Union[HTTPValidationError, SearchResponse]]:
    """Search Documents

    Args:
        index (AvailableInfiniGramIndexId):
        search (str):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.
        page (Union[Unset, int]):  Default: 0.
        page_size (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, SearchResponse]]
    """

    kwargs = _get_kwargs(
        index=index,
        search=search,
        maximum_document_display_length=maximum_document_display_length,
        page=page,
        page_size=page_size,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    index: AvailableInfiniGramIndexId,
    *,
    client: Union[AuthenticatedClient, Client],
    search: str,
    maximum_document_display_length: Union[Unset, int] = 10,
    page: Union[Unset, int] = 0,
    page_size: Union[Unset, int] = 10,
) -> Optional[Union[HTTPValidationError, SearchResponse]]:
    """Search Documents

    Args:
        index (AvailableInfiniGramIndexId):
        search (str):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.
        page (Union[Unset, int]):  Default: 0.
        page_size (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, SearchResponse]
    """

    return (
        await asyncio_detailed(
            index=index,
            client=client,
            search=search,
            maximum_document_display_length=maximum_document_display_length,
            page=page,
            page_size=page_size,
        )
    ).parsed
