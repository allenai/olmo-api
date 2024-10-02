from enum import Enum


class AvailableInfiniGramIndexId(str, Enum):
    DOLMA_1_7 = "dolma-1_7"
    PILEVAL_LLAMA = "pileval-llama"
    OLMOE_MIX_0924 = "olmoe-mix-0924"

    def __str__(self) -> str:
        return str(self.value)
