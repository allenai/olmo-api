import asyncio
from typing import Annotated

from fastapi import Depends, HTTPException, status

from api.attribution.attribution_request_models import AttributionResponse, GetAttributionRequest
from api.attribution.infini_gram_client import InfiniGramClientDependency
from api.attribution.process_attribution_response import process_attribution_response
from api.logging.fastapi_logger import FastAPIStructLogger
from infini_gram_api_client.api.default import get_document_attributions_index_attribution_post
from infini_gram_api_client.errors import UnexpectedStatus
from infini_gram_api_client.models.attribution_request import AttributionRequest
from infini_gram_api_client.models.available_infini_gram_index_id import (
    AvailableInfiniGramIndexId,
)
from infini_gram_api_client.models.problem import Problem
from infini_gram_api_client.models.request_validation_error import RequestValidationError

logger = FastAPIStructLogger()


class AttributionService:
    def __init__(self, infini_gram_client: InfiniGramClientDependency):
        self.infini_gram_client = infini_gram_client  # InfiniGramClient(base_url=settings.INFINIGRAM_API_URL, raise_on_unexpected_status=True)

    async def get_attribution(
        self, request: GetAttributionRequest, index: AvailableInfiniGramIndexId
    ) -> AttributionResponse:
        try:
            attribution_response = await get_document_attributions_index_attribution_post.asyncio(
                index=index,
                client=self.infini_gram_client,
                body=AttributionRequest(
                    response=request.model_response,
                    delimiters=["\n", "."],
                    allow_spans_with_partial_words=False,
                    minimum_span_length=1,
                    maximum_frequency=1000000,
                    maximum_span_density=0.05,
                    span_ranking_method="unigram_logprob_sum",
                    maximum_context_length=max(250, request.max_display_context_length),
                    maximum_context_length_long=request.max_display_context_length,
                    maximum_context_length_snippet=40,
                    maximum_documents_per_span=10,  # request.max_documents -- ??
                ),
            )
        except UnexpectedStatus as e:
            msg = f"Something went wrong when calling the infini-gram API: {e.status_code} {e.content.decode()}"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=msg) from e

        # translated all errors from werkzeug to fastapi HTTPExceptions
        # we could add a layer here, but this seems fine for now
        if isinstance(attribution_response, RequestValidationError):
            logger.exception(
                "infini-gram.api.validation_error", title=attribution_response.title, detail=attribution_response.errors
            )  # attribution_response.errors is complex-ish (nested stuff) -- may want to do something with it first?
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"infini-gram API reported a validation error: {attribution_response.title}\nThis is likely an error in olmo-api.",
            )

        if isinstance(attribution_response, Problem):
            logger.error("infini-gram.problem", title=attribution_response.title, detail=attribution_response.detail)

            if attribution_response.type_ == "server-overloaded":
                server_overloaded_msg = "OlmoTrace is currently overloaded. Please try again later."
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=server_overloaded_msg)

            server_error = f"infini-gram API reported an error: {attribution_response.title}"
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=server_error)

        if attribution_response is None:
            # raise exceptions.BadGateway(description="Something went wrong when calling the infini-gram API")
            bad_gateway_msg = "Something went wrong when calling the infini-gram API"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=bad_gateway_msg)

        if attribution_response.input_tokens is None:
            invalid_version = "The version of infinigram-api we hit doesn't support or didn't return input_tokens"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=invalid_version)

        # off-load attribution processing, scoring/flattening to own thread
        return await asyncio.to_thread(
            process_attribution_response,
            attribution_response=attribution_response,
            request=request,
            index=index,
        )


AttributionServiceDependency = Annotated[AttributionService, Depends()]
