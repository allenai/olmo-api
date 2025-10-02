from pydantic import BaseModel, Field

from src.inference.InferenceEngine import InferenceOptions


class TestFile(BaseModel):
    url: str
    mime: str

class TestCaseAcceptance(BaseModel):
    kind: str = Field(..., description='"exact", "contains", or "regex"')
    expected: str | int | float | list[str]


class TestCase(BaseModel):
    id: str
    input: str
    files: list[TestFile] | None = Field(default=None)
    acceptance: list[TestCaseAcceptance]


class ModelTestList(BaseModel):
    host: str
    model: str
    defaults: InferenceOptions
    tests: list[TestCase]


test_cases: list[ModelTestList] = [
    ModelTestList(
        host="cirrascale_backend",
        model="cs-OLMo-2-0325-32B-Instruct",
        defaults=InferenceOptions(max_tokens=64, temperature=0, n=1, top_p=1.0, logprobs=None, stop=[]),
        tests=[
            TestCase(
                id="arith-basic-2plus2",
                input="What is 2 + 2?",
                acceptance=[TestCaseAcceptance(kind="contains", expected="4")],
            ),
            TestCase(
                id="regex-date-format",
                input="Output today's date in ISO 8601 (YYYY-MM-DD) with no extras.",
                acceptance=[
                    TestCaseAcceptance(kind="regex", expected="^\\d{4}-\\d{2}-\\d{2}$")
                ]
            ),
        ],
    ),
    ModelTestList(
        host="cirrascale",
        model="mm-olmo-uber-model-v4-synthetic",
        defaults=InferenceOptions(max_tokens=64, temperature=0, n=1, top_p=1.0, logprobs=None, stop=[]),
        tests=[
            TestCase(
                id="contains-date-format",
                input="Point at the thumbs up icon",
                files=[TestFile(url="https://www.datocms-assets.com/64837/1751326409-sciarenathumbnail-v2.png", mime="image/png")],
                acceptance=[
                    TestCaseAcceptance(kind="contains", expected="</point>")
                ]
            ),
        ],
    ),
]

