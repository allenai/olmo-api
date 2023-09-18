from dataclasses import dataclass
from typing import Self, Any, Optional, Mapping

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
    total: int
    overflow: bool # if true, there are > 10k results

@dataclass
class SearchResults:
    meta: SearchMeta
    results: list[Result]

@dataclass
class Filters:
    sources: list[str]

class Client:
    def __init__(self, es: es8.Elasticsearch):
        self.es = es

    def search(self, qs: str, size: int, offset: int, filters: Optional[Filters] = None) -> SearchResults:
        # We use ElasticSearch's built in, "query string" query, which has a lot of
        # bells and whistles. See:
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html
        query: Mapping[str, Any] = {
            "bool": {
                "must": {
                    "query_string": {
                        "query": qs,
                        "default_field": "text"
                    },
                },
            }
        }
        if filters is not None:
            query["bool"]["filter"] = {
                "terms": {
                    "source": filters.sources
                }
            }
        res = self.es.search(
            index="docs",
            query=query,
            highlight={
                "fields": {
                        "text": {}
                }
            },
            size=size,
            from_=offset,
        )

        meta = SearchMeta(took_ms=res["took"], total=res["hits"]["total"]["value"],
                          overflow=res["hits"]["total"]["relation"] == "gte")
        results = [Result.from_hit(hit) for hit in res["hits"]["hits"]]

        return SearchResults(meta, results)

