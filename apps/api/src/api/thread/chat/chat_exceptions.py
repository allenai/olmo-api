from fastapi_problem.error import ServerProblem, UnprocessableProblem


class UnsupportedMediaTypeError(UnprocessableProblem): ...


class InvalidToolResponseError(ServerProblem): ...
