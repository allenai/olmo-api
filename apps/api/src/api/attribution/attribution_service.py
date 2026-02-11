import asyncio
from typing import Annotated

from fastapi import Depends, HTTPException, status

from api.attribution.infini_gram_client import InfiniGramClientDependency
from api.attribution.models.request import AttributionRequest
from api.attribution.models.response import AttributionResponse
from api.attribution.process_attribution import process_attribution
from api.logging.fastapi_logger import FastAPIStructLogger
from api.model_config.admin.model_config_admin_read_service import ModelConfigAdminReadServiceDependency
from api.service_errors import NotFoundError
from infini_gram_api_client.api.default import get_document_attributions_index_attribution_post
from infini_gram_api_client.errors import UnexpectedStatus
from infini_gram_api_client.models.attribution_request import AttributionRequest as InfiniGramAttributionRequest
from infini_gram_api_client.models.problem import Problem
from infini_gram_api_client.models.request_validation_error import RequestValidationError

logger = FastAPIStructLogger()


class AttributionService:
    def __init__(
        self,
        infini_gram_client: InfiniGramClientDependency,
        model_config_service: ModelConfigAdminReadServiceDependency,
    ):
        self.infini_gram_client = infini_gram_client
        self.model_config_service = model_config_service

    async def get_attribution(self, request: AttributionRequest) -> AttributionResponse:
        config = await self.model_config_service.get_one(request.model_id)
        if config is None:
            model_config_not_found = f"Model config {request.model_id} was not found."
            raise NotFoundError(model_config_not_found)

        if config.root.infini_gram_index is None:
            msg = f"Model {config.root.id} does not have an infini gram index configured"
            raise ValueError(msg)

        index = config.root.infini_gram_index

        try:
            infini_gram_response = await get_document_attributions_index_attribution_post.asyncio(
                index=index,
                client=self.infini_gram_client,
                body=InfiniGramAttributionRequest(
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
                    maximum_documents_per_span=10,  # do we want to use request.max_documents here?
                ),
            )
        except UnexpectedStatus as e:
            msg = f"Something went wrong when calling the infini-gram API: {e.status_code} {e.content.decode()}"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=msg) from e

        # translated all errors from werkzeug to fastapi HTTPExceptions
        # we could add a layer here, but this seems fine for now
        if isinstance(infini_gram_response, RequestValidationError):
            logger.exception(
                "infini-gram.api.validation_error", title=infini_gram_response.title, detail=infini_gram_response.errors
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"infini-gram API reported a validation error: {infini_gram_response.title}\nThis is likely an error in olmo-api.",
            )

        if isinstance(infini_gram_response, Problem):
            logger.error("infini-gram.problem", title=infini_gram_response.title, detail=infini_gram_response.detail)

            if infini_gram_response.type_ == "server-overloaded":
                server_overloaded_msg = "OlmoTrace is currently overloaded. Please try again later."
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=server_overloaded_msg)

            server_error = f"infini-gram API reported an error: {infini_gram_response.title}"
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=server_error)

        if infini_gram_response is None:
            bad_gateway_msg = "Something went wrong when calling the infini-gram API"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=bad_gateway_msg)

        if infini_gram_response.input_tokens is None:
            invalid_version = "The version of infinigram-api we hit doesn't support or didn't return input_tokens"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=invalid_version)

        # off-load attribution processing, scoring/flattening to own thread
        return await asyncio.to_thread(
            process_attribution,
            infini_gram_response=infini_gram_response,
            request=request,
            index=index,
        )


AttributionServiceDependency = Annotated[AttributionService, Depends()]
