from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi_problem.error import BadRequestProblem
from google.cloud.recaptchaenterprise_v1 import (
    Assessment,
    CreateAssessmentRequest,
    Event,
    RecaptchaEnterpriseServiceAsyncClient,
)
from opentelemetry import trace

from api.config import settings
from api.logging.fastapi_logger import FastAPIStructLogger

logger = FastAPIStructLogger()

tracer = trace.get_tracer(__name__)


@lru_cache
def get_default_recaptcha_service() -> "GoogleRecaptchaService":
    return GoogleRecaptchaService(
        project_id=settings.RECAPTCHA_GCP_PROJECT_ID,
        recaptcha_key=settings.RECAPTCHA_KEY,
    )


class GoogleRecaptchaService:
    def __init__(self, project_id: str, recaptcha_key: str):
        self.project_id = project_id
        self.recaptcha_key = recaptcha_key

    async def create_assessment(
        self,
        token: str,
        recaptcha_action: str,
        user_ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Assessment | None:
        """Create an assessment to analyze the risk of a UI action.
        Args:
            token: The generated token obtained from the client.
            recaptcha_action: Action name corresponding to the token.
        """

        client = RecaptchaEnterpriseServiceAsyncClient()

        # Set the properties of the event to be tracked.
        event = Event()
        event.site_key = self.recaptcha_key
        event.token = token
        event.expected_action = recaptcha_action

        if user_ip_address is not None:
            event.user_ip_address = user_ip_address
        if user_agent is not None:
            event.user_agent = user_agent

        assessment = Assessment()
        assessment.event = event

        project_name = f"projects/{self.project_id}"

        # Build the assessment request.
        request = CreateAssessmentRequest()
        request.assessment = assessment
        request.parent = project_name

        response = await client.create_assessment(request)

        return response

    @tracer.start_as_current_span(name="GoogleRecaptchaService/evaluate_text")
    async def evaluate_text(
        self, captcha_token: str, user_ip_address: str | None, user_agent: str | None, recaptcha_action: str
    ) -> None:
        captcha_assessment = await self.create_assessment(
            token=captcha_token,
            recaptcha_action=recaptcha_action,
            user_ip_address=user_ip_address,
            user_agent=user_agent,
        )

        if captcha_assessment is None or not captcha_assessment.token_properties.valid:
            invalid_captcha_message = "invalid_captcha"
            logger.info(invalid_captcha_message, assessment=captcha_assessment)
            raise BadRequestProblem(invalid_captcha_message)

        if (
            captcha_assessment.risk_analysis.score == 0.0
            or captcha_assessment.token_properties.action != recaptcha_action
        ):
            failed_captcha_assessment_message = "failed_captcha_assessment"
            logger.info(failed_captcha_assessment_message, assessment=captcha_assessment)
            raise BadRequestProblem(failed_captcha_assessment_message)


GoogleRecaptchaServiceDependency = Annotated[GoogleRecaptchaService, Depends(get_default_recaptcha_service)]
