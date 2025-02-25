from enum import StrEnum


class AvailableInfiniGramIndexId(StrEnum):
    OLMO_2_1124_13B = "olmo-2-1124-13b"
    PILEVAL_LLAMA = "pileval-llama"

    def __str__(self) -> str:
        return str(self.value)
