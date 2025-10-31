import json
import os
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime

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

    Note: This is kept for backward compatibility but FastAPI uses
    src/fastapi_json_response.py for JSON serialization.
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        if isinstance(obj, FileStorage):
            return obj.filename
        return json.JSONEncoder.default(self, obj)
