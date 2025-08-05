import base64
from collections.abc import Sequence

from flask import current_app
from werkzeug import exceptions
from werkzeug.datastructures import FileStorage

from src.bot_detection.create_assessment import create_assessment
from src.config.get_config import cfg
from src.message.GoogleModerateText import GoogleModerateText
from src.message.GoogleVisionSafeSearch import GoogleVisionSafeSearch
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckerType,
    SafetyCheckRequest,
)
from src.message.WildGuard import WildGuard


def check_message_safety(
    text: str,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
) -> bool | None:
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
