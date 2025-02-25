from enum import StrEnum


class SpanRankingMethod(StrEnum):
    LENGTH = "length"
    UNIGRAM_LOGPROB_SUM = "unigram_logprob_sum"

    def __str__(self) -> str:
        return str(self.value)
