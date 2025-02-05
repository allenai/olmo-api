from enum import Enum


class AvailableInfiniGramIndexId(str, Enum):
    OLMO_2_1124_13B = "olmo-2-1124-13b"
    PILEVAL_LLAMA = "pileval-llama"

    def __str__(self) -> str:
        return str(self.value)
