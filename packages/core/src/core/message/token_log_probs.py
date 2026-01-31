from dataclasses import dataclass


@dataclass
class TokenLogProbs:
    token_id: int
    text: str
    logprob: float
