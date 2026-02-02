from api.config import settings
from core.logger import CoreLogger


class FastAPIStructLogger(CoreLogger):
    def __init__(self, log_name: str = settings.LOG_NAME) -> None:
        super().__init__(log_name)
