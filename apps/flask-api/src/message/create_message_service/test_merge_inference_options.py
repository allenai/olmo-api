from db.models.message import Message
from db.models.model_config import ModelConfig, ModelHost, ModelType, PromptType
from db.models.inference_opts import InferenceOpts
from src.dao.message.message_models import Role
from src.message.create_message_service.merge_inference_options import (
    merge_inference_options,
)

test_model = ModelConfig(
    id="test-model",
    host=ModelHost.TestBackend,
    name="test model",
    description="test model",
    model_type=ModelType.Chat,
    model_id_on_host="test-model",
    internal=True,
    prompt_type=PromptType.TEXT_ONLY,
    temperature_default=0.0,
    temperature_upper=1.0,
    temperature_lower=0.0,
    temperature_step=0.1,
    top_p_default=1.0,
    top_p_upper=1.0,
    top_p_lower=0.0,
    top_p_step=0.1,
    max_tokens_default=2048,
    max_tokens_upper=2048,
    max_tokens_lower=1,
    max_tokens_step=1,
)


def test_get_inference_options_uses_default():
    parent_message = None

    inference_options = merge_inference_options(
        model=test_model,
        parent_message=parent_message,
        max_tokens=None,
        temperature=None,
        top_p=None,
        stop=None,
    )

    expected_inference_options = InferenceOpts(
        max_tokens=test_model.max_tokens_default,
        temperature=test_model.temperature_default,
        top_p=test_model.top_p_default,
        stop=test_model.stop_default,
    )

    assert inference_options == expected_inference_options


def test_get_inference_options_uses_options_from_parent():
    parent_inference_options = InferenceOpts(
        max_tokens=1337, temperature=0.9, top_p=0.1, stop=["test"], n=1, logprobs=1
    )

    parent_message = Message(
        id="test-message",
        content="test message",
        creator="test-user",
        role=Role.Assistant,
        opts=parent_inference_options,
        root="test-message",
        model_id="test-model",
        model_host="test_backend",
        parent=None,
        expiration_time=None,
    )

    inference_options = merge_inference_options(
        model=test_model,
        parent_message=parent_message,
        max_tokens=None,
        temperature=None,
        top_p=None,
        stop=None,
    )

    assert inference_options == parent_inference_options


def test_get_inference_options_uses_options_from_request_when_parent_present():
    parent_inference_options = InferenceOpts(
        max_tokens=1337, temperature=0.9, top_p=0.1, stop=["test"], n=1, logprobs=1
    )

    parent_message = Message(
        id="test-message",
        content="test message",
        creator="test-user",
        role=Role.Assistant,
        opts=parent_inference_options,
        root="test-message",
        model_id="test-model",
        model_host="test_backend",
        parent=None,
        expiration_time=None,
    )

    request_max_tokens = 100
    request_temperature = 0.7
    request_top_p = 0.7
    request_stop = ["request-stop"]

    inference_options = merge_inference_options(
        model=test_model,
        parent_message=parent_message,
        max_tokens=request_max_tokens,
        temperature=request_temperature,
        top_p=request_top_p,
        stop=request_stop,
    )

    expected_inference_options = InferenceOpts(
        max_tokens=request_max_tokens,
        temperature=request_temperature,
        top_p=request_top_p,
        stop=request_stop,
        n=parent_inference_options.n,
        logprobs=parent_inference_options.logprobs,
    )

    assert inference_options == expected_inference_options


def test_get_inference_options_uses_options_from_request_with_no_parent():
    parent_message = None

    request_max_tokens = 100
    request_temperature = 0.7
    # Setting this to None also lets us test that we get defaults from above in the chain
    request_top_p = None
    request_stop = ["request-stop"]

    inference_options = merge_inference_options(
        model=test_model,
        parent_message=parent_message,
        max_tokens=request_max_tokens,
        temperature=request_temperature,
        top_p=request_top_p,
        stop=request_stop,
    )

    expected_inference_options = InferenceOpts(
        max_tokens=request_max_tokens,
        temperature=request_temperature,
        top_p=test_model.top_p_default,
        stop=request_stop,
    )

    assert inference_options == expected_inference_options
