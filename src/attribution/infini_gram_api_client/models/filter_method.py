from enum import Enum


class FilterMethod(str, Enum):
    BM25 = "bm25"
    NONE = "none"

    def __str__(self) -> str:
        return str(self.value)
