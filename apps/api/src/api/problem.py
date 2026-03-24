from fastapi_problem.error import StatusProblem


class BadGatewayProblem(StatusProblem):
    type_ = "bad-gateway"
    status = 502


class ServiceUnavailableProblem(StatusProblem):
    type_ = "service-unavailable"
    status = 503
