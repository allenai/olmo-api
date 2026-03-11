import time

from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel


def get_test_model() -> Model:
    time.sleep(1)
    return TestModel()
