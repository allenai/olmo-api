from fastapi_problem.error import ServerProblem, UnprocessableProblem


class UnsupportedMediaTypeError(UnprocessableProblem): ...


class InvalidToolResponseError(ServerProblem): ...


class ModelNotFoundError(UnprocessableProblem):
    title = "Model not found"


class ModelNotAvailableError(UnprocessableProblem):
    title = "Model not available"


class UnhandledRoleError(ServerProblem): ...


class InvalidParentError(UnprocessableProblem): ...


class InappropriateTextError(UnprocessableProblem):
    title = "Inappropriate prompt text"
    type_ = "inappropriate_prompt_text"


class InappropriateFileError(UnprocessableProblem):
    title = "Inappropriate file"
    type_ = "inappropriate_file"


class FailedCaptchaError(UnprocessableProblem):
    title = "Failed captcha"
    type_ = "recaptcha"


class UnsupportedFileTypeError(UnprocessableProblem):
    title = "Unsupported file type"
    type_ = "unsupported_type"
