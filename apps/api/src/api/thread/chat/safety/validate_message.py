from fastapi_problem.error import ForbiddenProblem
from opentelemetry import trace

from api.auth.permission_service import PermissionServiceDependency
from api.config import settings
from api.logging.fastapi_logger import FastAPIStructLogger
from api.request_client import RequestClient
from api.thread.chat.chat_request import UserChatRequest
from api.thread.chat.safety.recaptcha_service import GoogleRecaptchaDependency
from core.auth import Permissions
from core.auth.token import Token

logger = FastAPIStructLogger()

tracer = trace.get_tracer(__name__)


class MessageValidationService:
    def __init__(self, captcha_service: GoogleRecaptchaDependency, permission_service: PermissionServiceDependency):
        self.captcha_service = captcha_service
        self.permission_service = permission_service

    @tracer.start_as_current_span(name="MessageValidationService/validate_security_and_safety")
    async def validate_security_and_safety(
        self, chat_request: UserChatRequest, request_client: RequestClient, user: Token
    ):
        recaptcha_action = "prompt_submission"

        if not user.is_anonymous_user and settings.RECAPTCHA_ENABLED and chat_request.captcha_token:
            await self.captcha_service.evaluate_text(
                captcha_token=chat_request.captcha_token,
                user_ip_address=request_client.ip_address,
                user_agent=request_client.user_agent,
                recaptcha_action=recaptcha_action,
            )

        can_bypass_safety_checks = self.permission_service.has_permission(
            user, permission=Permissions.WRITE_BYPASS_SAFETY_CHECKS
        )
        if can_bypass_safety_checks is False and chat_request.bypass_safety_check is True:
            cannot_bypass_safety_checks_message = "User is not allowed to change this setting"
            raise ForbiddenProblem(cannot_bypass_safety_checks_message)

        if can_bypass_safety_checks is True and chat_request.bypass_safety_check is True:
            return 0, None

        # Check prompt safety
        # Check Image safety
        # Check Video safety

        return
