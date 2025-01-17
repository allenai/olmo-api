from enum import Enum


class SpanRankingMethod(str, Enum):
    LENGTH = "length"
    UNIGRAM_LOGPROB_SUM = "unigram_logprob_sum"

    def __str__(self) -> str:
        return str(self.value)
