from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from src import obj

from .message.message import InferenceOpts, TokenLogProbs

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
    int,
]


def parse_logprobs(
    logprobs: list[list[dict[str, Any]]] | None,
) -> list[list[TokenLogProbs]] | None:
    if logprobs is None:
        return None
    return [[TokenLogProbs(**t) for t in lp] for lp in logprobs]


@dataclass
class CompletionOutput:
    text: str
    finish_reason: str
    logprobs: list[list[TokenLogProbs]] | None = None

    @staticmethod
    def from_dict(row: dict[str, Any]) -> "CompletionOutput":
        return CompletionOutput(
            row["text"],
            row["finish_reason"],
            parse_logprobs(row.get("logprobs")),
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
    def from_row(row: CompletionRow) -> "Completion":
        (
            id,
            input,
            outputs,
            opts,
            model,
            sha,
            created,
            tokms,
            genms,
            qms,
            intok,
            outok,
        ) = row
        return Completion(
            id,
            input,
            [CompletionOutput.from_dict(o) for o in outputs],
            InferenceOpts(**opts),
            model,
            sha,
            created,
            tokms,
            genms,
            qms,
            intok,
            outok,
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
        output_tokens: int,
    ) -> Completion:
        with self.pool.connection() as conn, conn.cursor() as cursor:
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
                Jsonb([asdict(o) for o in outputs]),
                Jsonb(opts.model_dump()),
                model,
                sha,
                tokenize_ms,
                generation_ms,
                queue_ms,
                input_tokens,
                output_tokens,
            )
            row = cursor.execute(q, values).fetchone()
            if row is None:
                msg = "failed to create completion"
                raise RuntimeError(msg)
            return Completion.from_row(row)

    def get(self, id: str) -> Completion | None:
        with self.pool.connection() as conn, conn.cursor() as cursor:
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

    def remove(self, ids: list[str]) -> None:
        if len(ids) == 0:
            return None

        with self.pool.connection() as conn, conn.cursor() as cursor:
            q = """
                    DELETE
                    FROM
                        completion
                    WHERE
                        id = ANY(%s)
                """
            cursor.execute(q, (ids,))
