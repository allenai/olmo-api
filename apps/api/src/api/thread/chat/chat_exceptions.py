from fastapi_problem.error import ServerProblem, UnprocessableProblem


class UnsupportedMediaTypeError(UnprocessableProblem): ...


class InvalidToolResponseError(ServerProblem): ...


class ModelNotFoundError(UnprocessableProblem):
    title = "Model not found"


class ModelNotAvailableError(UnprocessableProblem):
    title = "Model not available"


class UnhandledRoleError(ServerProblem): ...


class InvalidParentError(UnprocessableProblem): ...
