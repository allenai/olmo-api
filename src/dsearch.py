from dataclasses import dataclass
from typing import Self, Any

import elasticsearch8 as es8

HTML = str

@dataclass
class Result:
    id: str
    text: str
    source: str
    highlights: dict[str, list[HTML]]
    score: float

    @classmethod
    def from_hit(cls, hit: dict[str, Any]) -> Self:
        return cls(
            id=hit["_id"],
            text=hit["_source"]["text"],
            source=hit["_source"]["source"],
            highlights=hit["highlight"],
            score=hit["_score"],
        )

@dataclass
class SearchMeta:
    took_ms: int

@dataclass
class SearchResults:
    meta: SearchMeta
    results: list[Result]

class Client:
    def __init__(self, es: es8.Elasticsearch):
        self.es = es

    def search(self, query: str, size: int, offset: int) -> SearchResults:
        # We use ElasticSearch's built in, "query string" query, which has a lot of
        # bells and whistles. See:
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html
        res = self.es.search(
            index="docs",
            query={
                "query_string": {
                    "query": query,
                    "default_field": "text"
                },
            },
            highlight={
                "fields": {
                        "text": {}
                }
            },
            size=size,
            from_=offset,
        )

        meta = SearchMeta(took_ms=res["took"])
        results = [Result.from_hit(hit) for hit in res["hits"]["hits"]]

        return SearchResults(meta, results)

