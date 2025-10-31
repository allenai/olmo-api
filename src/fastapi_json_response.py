"""
FastAPI Custom JSON Response
-----------------------------

Custom JSON response class that handles datetime serialization to match
Flask's CustomJSONProvider behavior.
"""

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class CustomJSONResponse(JSONResponse):
    """
    Custom JSON response that serializes datetime objects to ISO format.

    This matches Flask's CustomJSONProvider behavior and ensures consistent
    datetime serialization across the API.
    """

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content, ensure_ascii=False, allow_nan=False, indent=None, separators=(",", ":"), default=self._custom_encoder
        ).encode("utf-8")

    @staticmethod
    def _custom_encoder(obj: Any) -> Any:
        """
        Custom encoder for non-JSON-serializable objects.

        Handles:
        - datetime and date objects → ISO format strings
        - Pydantic models → dict via model_dump()
        - dataclasses → dict via asdict()
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        msg = f"Object of type {type(obj).__name__} is not JSON serializable"
        raise TypeError(msg)
