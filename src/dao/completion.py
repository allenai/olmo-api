from psycopg_pool import ConnectionPool
from psycopg.types.json import Json
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, asdict
from .. import obj
from .message import InferenceOpts, LogProbs

CompletionRow = tuple[
    str,
    str,
    list[dict[str, Any]],
    dict[str, Any],
    str,
    str,
    datetime,
    int,
    int,
    int,
    int,
    int
]

@dataclass
class CompletionOutput:
    text: str
    finish_reason: str
    logprobs: Optional[list[LogProbs]]

    @staticmethod
    def from_dict(row: dict[str, Any]) -> 'CompletionOutput':
        return CompletionOutput(
            row['text'],
            row['finish_reason'],
            [LogProbs(**lp) for lp in row['logprobs']] if row['logprobs'] is not None else None
        )

@dataclass
class Completion:
    id: obj.ID
    input: str
    outputs: list[CompletionOutput]
    opts: InferenceOpts
    model: str
    sha: str
    created: datetime
    tokenize_ms: int
    generation_ms: int
    queue_ms: int
    input_tokens: int
    output_tokens: int

    @staticmethod
    def from_row(row: CompletionRow) -> 'Completion':
        id, input, outputs, opts, model, sha, created, tokms, genms, qms, intok, outok = row
        return Completion(
            id,
            input,
            [ CompletionOutput.from_dict(o) for o in outputs ],
            InferenceOpts(**opts),
            model,
            sha,
            created,
            tokms,
            genms,
            qms,
            intok,
            outok
        )

class Store:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(
        self,
        input: str,
        outputs: list[CompletionOutput],
        opts: InferenceOpts,
        model: str,
        sha: str,
        tokenize_ms: int,
        generation_ms: int,
        queue_ms: int,
        input_tokens: int,
        output_tokens: int
    ) -> Completion:
        with self.pool.connection() as conn:
            with conn.cursor() as cursor:
                q = """
                    INSERT INTO
                        completion (
                            id,
                            input,
                            outputs,
                            opts,
                            model,
                            sha,
                            tokenize_ms,
                            generation_ms,
                            queue_ms,
                            input_tokens,
                            output_tokens
                        )
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        input,
                        outputs,
                        opts,
                        model,
                        sha,
                        created,
                        tokenize_ms,
                        generation_ms,
                        queue_ms,
                        input_tokens,
                        output_tokens
                """
                values = (
                    obj.NewID("cpl"),
                    input,
                    Json([ asdict(o) for o in outputs ]),
                    Json(asdict(opts)),
                    model,
                    sha,
                    tokenize_ms,
                    generation_ms,
                    queue_ms,
                    input_tokens,
                    output_tokens
                )
                row = cursor.execute(q, values).fetchone()
                if row is None:
                    raise RuntimeError("failed to create completion")
                return Completion.from_row(row)

    def get(self, id: str) -> Optional[Completion]:
        with self.pool.connection() as conn:
            with conn.cursor() as cursor:
                q = """
                    SELECT
                        id,
                        input,
                        outputs,
                        opts,
                        model,
                        sha,
                        created,
                        tokenize_ms,
                        generation_ms,
                        queue_ms,
                        input_tokens,
                        output_tokens
                    FROM
                        completion
                    WHERE
                        id = %s
                """
                row = cursor.execute(q, (id,)).fetchone()
                return Completion.from_row(row) if row is not None else None

