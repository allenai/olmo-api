import json
import os
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any

from flask.json.provider import JSONProvider
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger
from werkzeug.datastructures import FileStorage


class StackdriverJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom log JSON log formatter that adds the severity member, allowing
    end users to filter logs by the level of the log message emitted.
    """

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["severity"] = record.levelname
        log_record["logger"] = record.name
        log_record["timestamp"] = datetime.now(UTC).isoformat()
        log_record["pid"] = os.getpid()


class CustomEncoder(json.JSONEncoder):
    """
    Custom JSONEncoder that:
    - emits datetime objects as ISO strings
    - handles dataclasses implicitly by calling asdict()
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, FileStorage):
            return obj.filename
        return json.JSONEncoder.default(self, obj)


class CustomJSONProvider(JSONProvider):
    """
    Flask JSONProvider that uses CustomEncoder.
    """

    def dumps(self, obj: Any, **kwargs: Any) -> str:
        kwargs.setdefault("ensure_ascii", True)
        kwargs.setdefault("sort_keys", True)
        kwargs.setdefault("indent", 2 if self._app.debug else None)
        kwargs.setdefault("cls", CustomEncoder)
        return json.dumps(obj, **kwargs)

    def loads(self, s: str | bytes, **kwargs: Any) -> Any:
        return json.loads(s, **kwargs)
