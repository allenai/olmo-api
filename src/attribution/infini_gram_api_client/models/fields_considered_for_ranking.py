from enum import Enum


class FieldsConsideredForRanking(str, Enum):
    PROMPT = "prompt"
    PROMPTRESPONSE = "prompt+response"
    RESPONSE = "response"

    def __str__(self) -> str:
        return str(self.value)
