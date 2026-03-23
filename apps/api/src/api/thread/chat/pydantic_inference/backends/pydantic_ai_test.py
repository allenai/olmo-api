from typing import TYPE_CHECKING

from pydantic_ai.models.test import TestModel

if TYPE_CHECKING:
    from pydantic_ai.models import Model


def get_test_model() -> Model:
    return TestModel()
