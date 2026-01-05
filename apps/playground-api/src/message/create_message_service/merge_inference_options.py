import src.dao.message.message_models as message
from db.models.message import Message
from db.models.model_config import ModelConfig


def merge_inference_options(
    model: ModelConfig,
    parent_message: Message | None,
    max_tokens: int | None,
    temperature: float | None,
    top_p: float | None,
    stop: list[str] | None,
) -> message.InferenceOpts:
    """
    Combines inference options from the model config, parent message, and request.

    The options are applied in this order this priority, with lower options overwriting higher:
    ```
    model config
    parent message
    request
    ```
    """
    # get the last inference options, either from the parent message or the model defaults if no parent
    default_inference_options = model.get_model_config_default_inference_options()
    parent_inference_options = message.InferenceOpts.from_message(parent_message)
    request_inference_options = message.InferenceOpts(
        max_tokens=max_tokens, temperature=temperature, top_p=top_p, stop=stop
    )

    merged_inference_options = (
        default_inference_options.model_dump()
        # Excluding None from these lets us keep the options from the higher set of options
        | (
            parent_inference_options.model_dump(exclude_none=True)
            if parent_inference_options is not None
            else {}
        )
        | request_inference_options.model_dump(exclude_none=True)
    )

    return message.InferenceOpts.model_validate(merged_inference_options)
