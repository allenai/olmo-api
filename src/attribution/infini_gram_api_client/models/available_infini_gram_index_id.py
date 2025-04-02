from enum import Enum


class AvailableInfiniGramIndexId(str, Enum):
    OLMOE_0125_1B_7B = "olmoe-0125-1b-7b"
    OLMO_2_0325_32B = "olmo-2-0325-32b"
    OLMO_2_1124_13B = "olmo-2-1124-13b"
    PILEVAL_LLAMA = "pileval-llama"

    def __str__(self) -> str:
        return str(self.value)
