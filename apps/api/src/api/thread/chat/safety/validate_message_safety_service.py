from collections.abc import Sequence
from mimetypes import guess_type
from typing import Annotated, Final

from fastapi import Depends, UploadFile
from fastapi_problem.error import BadRequestProblem, ForbiddenProblem
from opentelemetry import trace

from api.auth.optional_auth_user import OptionalAuthUser
from api.auth.permission_service import PermissionServiceDependency
from api.config import settings
from api.logging.fastapi_logger import FastAPIStructLogger
from api.request_client import RequestClientDependency
from api.thread.chat.chat_request import ChatRequest
from api.thread.chat.safety.video_safety_checker_service import VideoSafetyCheckerServiceDependency
from core.auth import Permissions

from .google_recaptcha_service import GoogleRecaptchaServiceDependency
from .safety_checkers.safety_checker_base import SafetyCheckRequest
from .text_safety_checker_service import TextSafetyCheckerServiceDependency

logger = FastAPIStructLogger()

tracer = trace.get_tracer(__name__)

RECAPTCHA_ACTION_PROMPT_ACTION: Final[str] = "prompt_submission"


def split_files(
    files: Sequence[UploadFile] | None,
) -> tuple[Sequence[UploadFile], Sequence[UploadFile], Sequence[UploadFile]]:

    video_files: list[UploadFile] = []
    image_files: list[UploadFile] = []
    unsupported_files: list[UploadFile] = []

    if files is not None:
        for file in files or []:
            mime_type, _encoding = guess_type(file.filename) if file.filename else (None, None)
            file_type = mime_type or file.content_type or ""

            if file_type.startswith("video/"):
                video_files.append(file)
            elif file_type.startswith("image/"):
                image_files.append(file)
            else:
                unsupported_files.append(file)

    return image_files, video_files, unsupported_files


class ValidateMessageSafetyService:
    def __init__(
        self,
        recaptcha_service: GoogleRecaptchaServiceDependency,
        permission_service: PermissionServiceDependency,
        text_safety_checker_service: TextSafetyCheckerServiceDependency,
        video_safety_checker_service: VideoSafetyCheckerServiceDependency,
        request_client: RequestClientDependency,
        user: OptionalAuthUser,
    ):
        self.recaptcha_service = recaptcha_service
        self.permission_service = permission_service
        self.text_safety_checker_service = text_safety_checker_service
        self.video_safety_checker_service = video_safety_checker_service
        self.request_client = request_client
        self.user = user

    async def _can_bypass_safety_checks(self, request: ChatRequest):
        # Bypass safety
        #
        can_bypass_safety_checks = self.permission_service.has_permission(
            self.user, permission=Permissions.WRITE_BYPASS_SAFETY_CHECKS
        )
        if can_bypass_safety_checks is False and request.bypass_safety_check is True:
            cannot_bypass_safety_checks_message = "User is not allowed to change this setting"
            raise ForbiddenProblem(cannot_bypass_safety_checks_message)

        return can_bypass_safety_checks is True and request.bypass_safety_check is True

    async def _check_text(self, text: str | None) -> bool | None:
        if text is None:
            return True

        try:
            result = await self.text_safety_checker_service.check_request(SafetyCheckRequest(content=text))
            return result.is_safe()
        except Exception:
            logger.exception("text_safety_checker_error")

        return None

    @tracer.start_as_current_span(name="ValidateMessageSafetyService/validate_before")
    async def validate_before(self, request: ChatRequest):
        # Recaptcha
        # chat_request.captcha_token is required and validated in `env.PRODUCTION` environement
        #
        if settings.RECAPTCHA_ENABLED and request.captcha_token:
            await self.recaptcha_service.evaluate_text(
                captcha_token=request.captcha_token,
                user_ip_address=self.request_client.ip_address,
                user_agent=self.request_client.user_agent,
                recaptcha_action=RECAPTCHA_ACTION_PROMPT_ACTION,
                is_anonymous_user=self.user.is_anonymous_user,
            )

        await self._check_text(text=request.content)

    async def validate_after(
        self,
        message_id: str,
        request: ChatRequest,
    ):
        if await self._can_bypass_safety_checks(request=request):
            return

        image_files, video_files, unsupported_files = split_files(request.files)

        if unsupported_files:
            unsupported_names = [f.filename for f in unsupported_files]
            logger.warning(
                "check_video.unsupported_type",
                files=unsupported_names,
            )
            msg = "Unsupported file types in input"
            raise BadRequestProblem(msg)

        is_video_safe = await self.video_safety_checker_service.check_video_safety(
            files=video_files, message_id=message_id
        )

        # TODO: Image safety

        if is_video_safe is False:
            inappropriate_video_message = "Video was flagged as inappropriate"
            raise BadRequestProblem(inappropriate_video_message)

        return


ValidateMessageSafetyServiceDependency = Annotated[ValidateMessageSafetyService, Depends()]
