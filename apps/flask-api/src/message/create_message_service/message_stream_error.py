from core.api_interface import APIInterface
from core.object_id import ID


class MessageStreamError(APIInterface):
    message: ID
    error: str
    reason: str
