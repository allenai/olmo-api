from enum import Enum


class AvailableInfiniGramIndexId(str, Enum):
    DOLMA_1_7 = "dolma-1_7"
    OLMOE = "olmoe"
    OLMOE_MIX_0924 = "olmoe-mix-0924"
    OLMO_2_1124_13B = "olmo-2-1124-13b"
    PILEVAL_LLAMA = "pileval-llama"

    def __str__(self) -> str:
        return str(self.value)
