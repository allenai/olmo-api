import base64
from collections.abc import Sequence
from time import time_ns

from flask import current_app
from opentelemetry import trace
from werkzeug import exceptions
from werkzeug.datastructures import FileStorage

from otel.default_tracer import get_default_tracer
from src.auth.auth_utils import Permissions, user_has_permission
from src.auth.token import Token
from src.bot_detection.create_assessment import create_assessment
from src.config.get_config import cfg
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)
from src.message.GoogleModerateText import GoogleModerateText
from src.message.GoogleVisionSafeSearch import GoogleVisionSafeSearch
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckerType,
    SafetyCheckRequest,
)
from src.message.WildGuard import WildGuard

tracer = get_default_tracer()


@tracer.start_as_current_span("check_text_safety")
def check_message_safety(
    text: str,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
) -> bool | None:
    trace.get_current_span().set_attribute("safety_checker_type", checker_type)
    safety_checker: SafetyChecker = GoogleModerateText()
    request = SafetyCheckRequest(content=text)

    if checker_type == SafetyCheckerType.WildGuard:
        safety_checker = WildGuard()

    try:
        result = safety_checker.check_request(request)

        return result.is_safe()

    except Exception as e:
        current_app.logger.exception("Skipped message safety check due to error: %s. ", repr(e))

    return None


@tracer.start_as_current_span("check_image_safety")
def check_image_safety(files: Sequence[FileStorage]) -> bool | None:
    checker = GoogleVisionSafeSearch()

    for file in files:
        try:
            image = base64.b64encode(file.stream.read()).decode("utf-8")
            file.stream.seek(0)

            request = SafetyCheckRequest(image, file.filename)
            result = checker.check_request(request)

            if not result.is_safe():
                return False

        except Exception as e:
            current_app.logger.exception(
                "Skipped image safety check over %s due to error: %s. ",
                file.filename,
                repr(e),
            )

            return None

    return True


@tracer.start_as_current_span("evaluate_prompt_submission_captcha")
def evaluate_prompt_submission_captcha(
    captcha_token: str | None, user_ip_address: str | None, user_agent: str | None, *, is_anonymous_user: bool
):
    prompt_submission_action = "prompt_submission"
    if cfg.google_cloud_services.recaptcha_key is not None and captcha_token is not None:
        captcha_assessment = create_assessment(
            project_id="ai2-reviz",
            recaptcha_key=cfg.google_cloud_services.recaptcha_key,
            token=captcha_token,
            recaptcha_action=prompt_submission_action,
            user_ip_address=user_ip_address,
            user_agent=user_agent,
        )

        if not is_anonymous_user or not cfg.google_cloud_services.enable_recaptcha:
            return

        logger = current_app.logger

        if captcha_assessment is None or not captcha_assessment.token_properties.valid:
            logger.info("rejecting message request due to invalid captcha", extra={"assessment": captcha_assessment})
            invalid_captcha_message = "invalid_captcha"
            raise exceptions.BadRequest(invalid_captcha_message)

        if (
            captcha_assessment.risk_analysis.score == 0.0
            or captcha_assessment.token_properties.action != prompt_submission_action
        ):
            logger.info(
                "rejecting message request due to failed captcha assessment", extra={"assessment": captcha_assessment}
            )
            failed_captcha_assessment_message = "failed_captcha_assessment"
            raise exceptions.BadRequest(failed_captcha_assessment_message)


INAPPROPRIATE_TEXT_ERROR = "inappropriate_prompt_text"
INAPPROPRIATE_FILE_ERROR = "inappropriate_prompt_file"

FORRBIDDEN_SETTING = "User is not allowed to change this setting"


@tracer.start_as_current_span("validate_message_security_and_safety")
def validate_message_security_and_safety(
    request: CreateMessageRequestWithFullMessages,
    client_auth: Token,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
    user_ip_address: str | None = None,
    user_agent: str | None = None,
):
    evaluate_prompt_submission_captcha(
        captcha_token=request.captcha_token,
        user_ip_address=user_ip_address,
        user_agent=user_agent,
        is_anonymous_user=client_auth.is_anonymous_user,
    )

    can_bypass_safety_checks = user_has_permission(client_auth.token, Permissions.WRITE_BYPASS_SAFETY_CHECKS)

    if can_bypass_safety_checks is False and request.bypass_safety_check is True:
        raise exceptions.Forbidden(FORRBIDDEN_SETTING)

    if can_bypass_safety_checks is True and request.bypass_safety_check is True:
        return 0, None

    safety_check_start_time = time_ns()
    is_content_safe = check_message_safety(request.content, checker_type=checker_type)
    is_image_safe = check_image_safety(files=request.files or [])
    safety_check_elapsed_time = (time_ns() - safety_check_start_time) // 1_000_000

    if is_content_safe is False:
        raise exceptions.BadRequest(INAPPROPRIATE_TEXT_ERROR)

    if is_image_safe is False:
        raise exceptions.BadRequest(INAPPROPRIATE_FILE_ERROR)

    is_message_harmful = None if is_content_safe is None or is_image_safe is None else False

    return safety_check_elapsed_time, is_message_harmful
