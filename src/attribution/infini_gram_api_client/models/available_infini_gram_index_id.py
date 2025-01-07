from enum import Enum


class AvailableInfiniGramIndexId(str, Enum):
    PILEVAL_LLAMA = "pileval-llama"
    DOLMA_1_7 = "dolma-1_7"
    OLMOE_MIX_0924 = "olmoe-mix-0924"
    OLMOE = "olmoe"
    OLMO_2_1124_13B = "olmo-2-1124-13b"

    def __str__(self) -> str:
        return str(self.value)
