from enum import IntEnum


class Rating(IntEnum):
    FLAG = -1
    NEGATIVE = 0
    POSITIVE = 1


EXCLUSIVE_RATINGS = {Rating.POSITIVE, Rating.NEGATIVE}
