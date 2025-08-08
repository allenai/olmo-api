from src import db
from src.model_config.get_model_config_service import ModelResponse


def save_pydantic_message(response: ModelResponse, dbc: db.Client): ...


def save_inference_engine_message(dbc: db.Client): ...
