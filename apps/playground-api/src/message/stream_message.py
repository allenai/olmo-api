from dataclasses import dataclass


@dataclass
class StreamMetrics:
    first_chunk_ns: int | None
    input_token_count: int | None
    output_token_count: int | None
    total_generation_ns: int | None
