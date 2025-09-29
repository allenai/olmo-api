from src.dao.engine_models.model_config import ModelConfig, ModelHost, ModelType, PromptType
from src.dao.message.message_models import InferenceOpts
from src.pydantic_inference.pydantic_ai_helpers import pydantic_settings_map

default_inference_constraints = {
    "max_tokens_default": 2048,
    "max_tokens_upper": 2048,
    "max_tokens_lower": 1,
    "max_tokens_step": 1,
    "temperature_default": 0.7,
    "temperature_upper": 1.0,
    "temperature_lower": 0.0,
    "temperature_step": 0.01,
    "top_p_default": 1.0,
    "top_p_upper": 1.0,
    "top_p_lower": 0.0,
    "top_p_step": 0.01,
    "stop_default": None,
}


class TestPydanticSettingsMap:
    def test_should_map_all_opts_when_passed(self):
        opts = InferenceOpts(max_tokens=1000, temperature=0.5, top_p=0.05, n=1, logprobs=None, stop=["/n", "<end>"])
        model_config = ModelConfig(
            id="test-model",
            host=ModelHost.TestBackend,
            name="Test Model",
            description="Test model",
            model_type=ModelType.Chat,
            model_id_on_host="test-model",
            internal=True,
            prompt_type=PromptType.TEXT_ONLY,
            can_think=False,
            **default_inference_constraints,
        )

        result = pydantic_settings_map(opts=opts, model_config=model_config)

        assert result.get("max_tokens") == opts.max_tokens
        assert result.get("temperature") == opts.temperature
        assert result.get("top_p") == opts.top_p
        assert result.get("stop_sequences") == opts.stop

        assert result.get("openai_reasoning_effort") is None

        assert result.get("extra_body") is None

    def test_should_map_reasoning_effort_when_thinking_enabled(self):
        opts = InferenceOpts(max_tokens=1000, temperature=0.5, top_p=0.05, n=1, logprobs=None, stop=["/n", "<end>"])
        model_config = ModelConfig(
            id="test-model",
            host=ModelHost.TestBackend,
            name="Test Model",
            description="Test model",
            model_type=ModelType.Chat,
            model_id_on_host="test-model",
            internal=True,
            prompt_type=PromptType.TEXT_ONLY,
            can_think=True,
            **default_inference_constraints,
        )

        result = pydantic_settings_map(opts=opts, model_config=model_config)

        assert result.get("openai_reasoning_effort") == "low"

    def test_should_pass_extra_body_through(self):
        opts = InferenceOpts(max_tokens=1000, temperature=0.5, top_p=0.05, n=1, logprobs=None, stop=["/n", "<end>"])
        model_config = ModelConfig(
            id="test-model",
            host=ModelHost.TestBackend,
            name="Test Model",
            description="Test model",
            model_type=ModelType.Chat,
            model_id_on_host="test-model",
            internal=True,
            prompt_type=PromptType.TEXT_ONLY,
            can_think=False,
            **default_inference_constraints,
        )
        extra_body = {"foo": "bar", "number": 42}

        result = pydantic_settings_map(opts=opts, model_config=model_config, extra_body=extra_body)

        assert result.get("extra_body") == extra_body
