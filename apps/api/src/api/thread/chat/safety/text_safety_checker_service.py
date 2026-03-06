from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from .safety_checkers.google_text_safety_checker import GoogleTextSafetyChecker
from .safety_checkers.safety_checker_base import TextSafetyChecker


@lru_cache
def get_text_safety_checker() -> TextSafetyChecker:
    return GoogleTextSafetyChecker()


TextSafetyCheckerServiceDependency = Annotated[TextSafetyChecker, Depends(get_text_safety_checker)]
