from pythonjsonlogger import jsonlogger
from datetime import datetime, timezone
from flask.json.provider import JSONProvider
from typing import Any
from dataclasses import is_dataclass, asdict

import json

class StackdriverJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom log JSON log formatter that adds the severity member, allowing
    end users to filter logs by the level of the log message emitted.
    """
    def add_fields(self, log_record, record, message_dict):
        super(StackdriverJsonFormatter, self).add_fields(log_record, record,
            message_dict)
        log_record['severity'] = record.levelname
        log_record['logger' ] = record.name
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()

class CustomEncoder(json.JSONEncoder):
    """
    Custom JSONEncoder that:
    - emits datetime objects as ISO strings
    - handles dataclasses implicitly by calling asdict()
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if is_dataclass(obj):
            return asdict(obj)
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
