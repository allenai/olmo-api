from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from ...models.infini_gram_document_response import InfiniGramDocumentResponse
from ...models.request_validation_error import RequestValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    index: AvailableInfiniGramIndexId,
    document_index: int,
    *,
    maximum_document_display_length: Union[Unset, int] = 10,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["maximum_document_display_length"] = maximum_document_display_length

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/{index}/documents/{document_index}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[InfiniGramDocumentResponse, RequestValidationError]]:
    if response.status_code == 200:
        response_200 = InfiniGramDocumentResponse.from_dict(response.json())

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
) -> Response[Union[InfiniGramDocumentResponse, RequestValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    index: AvailableInfiniGramIndexId,
    document_index: int,
    *,
    client: Union[AuthenticatedClient, Client],
    maximum_document_display_length: Union[Unset, int] = 10,
) -> Response[Union[InfiniGramDocumentResponse, RequestValidationError]]:
    """Get Document By Index

    Args:
        index (AvailableInfiniGramIndexId):
        document_index (int):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[InfiniGramDocumentResponse, RequestValidationError]]
    """

    kwargs = _get_kwargs(
        index=index,
        document_index=document_index,
        maximum_document_display_length=maximum_document_display_length,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    index: AvailableInfiniGramIndexId,
    document_index: int,
    *,
    client: Union[AuthenticatedClient, Client],
    maximum_document_display_length: Union[Unset, int] = 10,
) -> Optional[Union[InfiniGramDocumentResponse, RequestValidationError]]:
    """Get Document By Index

    Args:
        index (AvailableInfiniGramIndexId):
        document_index (int):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[InfiniGramDocumentResponse, RequestValidationError]
    """

    return sync_detailed(
        index=index,
        document_index=document_index,
        client=client,
        maximum_document_display_length=maximum_document_display_length,
    ).parsed


async def asyncio_detailed(
    index: AvailableInfiniGramIndexId,
    document_index: int,
    *,
    client: Union[AuthenticatedClient, Client],
    maximum_document_display_length: Union[Unset, int] = 10,
) -> Response[Union[InfiniGramDocumentResponse, RequestValidationError]]:
    """Get Document By Index

    Args:
        index (AvailableInfiniGramIndexId):
        document_index (int):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[InfiniGramDocumentResponse, RequestValidationError]]
    """

    kwargs = _get_kwargs(
        index=index,
        document_index=document_index,
        maximum_document_display_length=maximum_document_display_length,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    index: AvailableInfiniGramIndexId,
    document_index: int,
    *,
    client: Union[AuthenticatedClient, Client],
    maximum_document_display_length: Union[Unset, int] = 10,
) -> Optional[Union[InfiniGramDocumentResponse, RequestValidationError]]:
    """Get Document By Index

    Args:
        index (AvailableInfiniGramIndexId):
        document_index (int):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[InfiniGramDocumentResponse, RequestValidationError]
    """

    return (
        await asyncio_detailed(
            index=index,
            document_index=document_index,
            client=client,
            maximum_document_display_length=maximum_document_display_length,
        )
    ).parsed
