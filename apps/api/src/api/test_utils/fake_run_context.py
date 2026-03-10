from pydantic_ai import RunContext, RunUsage

from api.thread.chat.pydantic_inference.backends.pydantic_ai_test import get_test_model


def make_fake_run_context():
    return RunContext(deps=None, model=get_test_model(), usage=RunUsage())
