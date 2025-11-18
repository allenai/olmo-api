from enum import Enum


class AvailableInfiniGramIndexId(str, Enum):
    OLMOE_0125_1B_7B = "olmoe-0125-1b-7b"
    OLMO_2_0325_32B = "olmo-2-0325-32b"
    OLMO_2_1124_13B = "olmo-2-1124-13b"
    OLMO_3_0625_32B_THINK = "olmo-3-0625-32b-think"
    OLMO_3_0625_7B_INSTRUCT = "olmo-3-0625-7b-instruct"
    OLMO_3_0625_7B_THINK = "olmo-3-0625-7b-think"
    PILEVAL_LLAMA = "pileval-llama"
    TULU_3_405B = "tulu-3-405b"
    TULU_3_70B = "tulu-3-70b"
    TULU_3_8B = "tulu-3-8b"

    def __str__(self) -> str:
        return str(self.value)
