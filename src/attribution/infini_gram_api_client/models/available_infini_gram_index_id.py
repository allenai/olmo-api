from enum import Enum


class AvailableInfiniGramIndexId(str, Enum):
    DOLMA_1_7 = "dolma-1_7"
    PILEVAL_LLAMA = "pileval-llama"

    def __str__(self) -> str:
        return str(self.value)
