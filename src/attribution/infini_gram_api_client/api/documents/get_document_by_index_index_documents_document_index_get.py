from http import HTTPStatus
from typing import Any

import httpx

from src.attribution.infini_gram_api_client import errors
from src.attribution.infini_gram_api_client.client import AuthenticatedClient, Client
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from src.attribution.infini_gram_api_client.models.http_validation_error import HTTPValidationError
from src.attribution.infini_gram_api_client.models.infini_gram_document_response import InfiniGramDocumentResponse
from src.attribution.infini_gram_api_client.types import UNSET, Response, Unset


def _get_kwargs(
    index: AvailableInfiniGramIndexId,
    document_index: int,
    *,
    maximum_document_display_length: Unset | int = 10,
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
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | InfiniGramDocumentResponse | None:
    if response.status_code == 200:
        return InfiniGramDocumentResponse.from_dict(response.json())

    if response.status_code == 422:
        return HTTPValidationError.from_dict(response.json())

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | InfiniGramDocumentResponse]:
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
    client: AuthenticatedClient | Client,
    maximum_document_display_length: Unset | int = 10,
) -> Response[HTTPValidationError | InfiniGramDocumentResponse]:
    """Get Document By Index

    Args:
        index (AvailableInfiniGramIndexId):
        document_index (int):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, InfiniGramDocumentResponse]]
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
    client: AuthenticatedClient | Client,
    maximum_document_display_length: Unset | int = 10,
) -> HTTPValidationError | InfiniGramDocumentResponse | None:
    """Get Document By Index

    Args:
        index (AvailableInfiniGramIndexId):
        document_index (int):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, InfiniGramDocumentResponse]
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
    client: AuthenticatedClient | Client,
    maximum_document_display_length: Unset | int = 10,
) -> Response[HTTPValidationError | InfiniGramDocumentResponse]:
    """Get Document By Index

    Args:
        index (AvailableInfiniGramIndexId):
        document_index (int):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, InfiniGramDocumentResponse]]
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
    client: AuthenticatedClient | Client,
    maximum_document_display_length: Unset | int = 10,
) -> HTTPValidationError | InfiniGramDocumentResponse | None:
    """Get Document By Index

    Args:
        index (AvailableInfiniGramIndexId):
        document_index (int):
        maximum_document_display_length (Union[Unset, int]):  Default: 10.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, InfiniGramDocumentResponse]
    """

    return (
        await asyncio_detailed(
            index=index,
            document_index=document_index,
            client=client,
            maximum_document_display_length=maximum_document_display_length,
        )
    ).parsed
