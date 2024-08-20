from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.attribution_request import AttributionRequest
from ...models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from ...models.http_validation_error import HTTPValidationError
from ...models.infini_gram_attribution_response import InfiniGramAttributionResponse
from ...models.infini_gram_attribution_response_with_documents import InfiniGramAttributionResponseWithDocuments
from ...types import Response


def _get_kwargs(
    index: AvailableInfiniGramIndexId,
    *,
    body: AttributionRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/{index}/attribution",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[HTTPValidationError, Union["InfiniGramAttributionResponse", "InfiniGramAttributionResponseWithDocuments"]]
]:
    if response.status_code == HTTPStatus.OK:

        def _parse_response_200(
            data: object,
        ) -> Union["InfiniGramAttributionResponse", "InfiniGramAttributionResponseWithDocuments"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_1 = InfiniGramAttributionResponseWithDocuments.from_dict(data)

                return response_200_type_1
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_0 = InfiniGramAttributionResponse.from_dict(data)

            return response_200_type_0

        response_200 = _parse_response_200(response.json())

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
) -> Response[
    Union[HTTPValidationError, Union["InfiniGramAttributionResponse", "InfiniGramAttributionResponseWithDocuments"]]
]:
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
    body: AttributionRequest,
) -> Response[
    Union[HTTPValidationError, Union["InfiniGramAttributionResponse", "InfiniGramAttributionResponseWithDocuments"]]
]:
    """Get Document Attributions

    Args:
        index (AvailableInfiniGramIndexId):
        body (AttributionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Union['InfiniGramAttributionResponse', 'InfiniGramAttributionResponseWithDocuments']]]
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
    client: Union[AuthenticatedClient, Client],
    body: AttributionRequest,
) -> Optional[
    Union[HTTPValidationError, Union["InfiniGramAttributionResponse", "InfiniGramAttributionResponseWithDocuments"]]
]:
    """Get Document Attributions

    Args:
        index (AvailableInfiniGramIndexId):
        body (AttributionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Union['InfiniGramAttributionResponse', 'InfiniGramAttributionResponseWithDocuments']]
    """

    return sync_detailed(
        index=index,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    index: AvailableInfiniGramIndexId,
    *,
    client: Union[AuthenticatedClient, Client],
    body: AttributionRequest,
) -> Response[
    Union[HTTPValidationError, Union["InfiniGramAttributionResponse", "InfiniGramAttributionResponseWithDocuments"]]
]:
    """Get Document Attributions

    Args:
        index (AvailableInfiniGramIndexId):
        body (AttributionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Union['InfiniGramAttributionResponse', 'InfiniGramAttributionResponseWithDocuments']]]
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
    client: Union[AuthenticatedClient, Client],
    body: AttributionRequest,
) -> Optional[
    Union[HTTPValidationError, Union["InfiniGramAttributionResponse", "InfiniGramAttributionResponseWithDocuments"]]
]:
    """Get Document Attributions

    Args:
        index (AvailableInfiniGramIndexId):
        body (AttributionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Union['InfiniGramAttributionResponse', 'InfiniGramAttributionResponseWithDocuments']]
    """

    return (
        await asyncio_detailed(
            index=index,
            client=client,
            body=body,
        )
    ).parsed
