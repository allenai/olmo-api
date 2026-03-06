from typing import Annotated

from fastapi import Depends
from fastapi_problem.error import BadRequestProblem, ForbiddenProblem
from opentelemetry import trace

from api.auth.permission_service import PermissionServiceDependency
from api.config import settings
from api.logging.fastapi_logger import FastAPIStructLogger
from api.request_client import RequestClient
from api.thread.chat.chat_request import ChatRequest
from core.auth import Permissions
from core.auth.token import Token

from .google_recaptcha_service import GoogleRecaptchaServiceDependency
from .safety_checkers.safety_checker_base import SafetyCheckRequest
from .text_safety_checker_service import TextSafetyCheckerServiceDependency

logger = FastAPIStructLogger()

tracer = trace.get_tracer(__name__)


class ValidateMessageSafetyService:
    def __init__(
        self,
        recaptcha_service: GoogleRecaptchaServiceDependency,
        permission_service: PermissionServiceDependency,
        text_safety_checker_service: TextSafetyCheckerServiceDependency,
    ):
        self.recaptcha_service = recaptcha_service
        self.permission_service = permission_service
        self.text_safety_checker_service = text_safety_checker_service

    async def _check_text(self, text: str | None) -> bool | None:
        # Hmmm
        if text is None:
            return True

        try:
            result = await self.text_safety_checker_service.check_request(SafetyCheckRequest(content=text))
            return result.is_safe()
        except Exception:
            logger.exception("text_safety_checker_error")

        return None

    @tracer.start_as_current_span(name="ValidateMessageSafetyService/validate")
    async def validate(  # UserChatRequest ?
        self,
        chat_request: ChatRequest,
        request_client: RequestClient,
        user: Token,  # could inject this also
    ):
        # Recaptcha
        #
        recaptcha_action = "prompt_submission"

        if not user.is_anonymous_user and settings.RECAPTCHA_ENABLED and chat_request.captcha_token:
            await self.recaptcha_service.evaluate_text(
                captcha_token=chat_request.captcha_token,
                user_ip_address=request_client.ip_address,
                user_agent=request_client.user_agent,
                recaptcha_action=recaptcha_action,
            )

        # Bypass safety?
        #
        can_bypass_safety_checks = self.permission_service.has_permission(
            user, permission=Permissions.WRITE_BYPASS_SAFETY_CHECKS
        )
        if can_bypass_safety_checks is False and chat_request.bypass_safety_check is True:
            cannot_bypass_safety_checks_message = "User is not allowed to change this setting"
            raise ForbiddenProblem(cannot_bypass_safety_checks_message)

        if can_bypass_safety_checks is True and chat_request.bypass_safety_check is True:
            return

        # Check message contents
        #
        is_text_safe = await self._check_text(chat_request.content)

        # TODO: check everything else
        # Check Image safety
        # Check Video safety

        # throw errors after validation
        if is_text_safe is False:
            inappropriate_text_msg = "Text was flagged as inappropriate"
            raise BadRequestProblem(inappropriate_text_msg)

        return


ValidateMessageSafetyServiceDependency = Annotated[ValidateMessageSafetyService, Depends()]
