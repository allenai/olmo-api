from pydantic import AwareDatetime, Field

from core import object_id as obj
from core.api_interface import APIInterface
from core.label.rating import Rating


class Label(APIInterface):
    id: obj.ID
    message: str
    rating: Rating
    creator: str
    comment: str | None = Field(default=None)
    created: AwareDatetime
    deleted: AwareDatetime | None = Field(default=None)
