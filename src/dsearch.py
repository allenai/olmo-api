from dataclasses import dataclass, field
from typing import Self, Any, Optional, Mapping

import elasticsearch8 as es8

HTML = str

def first_n_words(s: str, n: int) -> str:
    # We take the first n * 32 characters as to avoid processing the entire text, which might be
    # large. This is for obvious reasons imperfect but probably good enough for manifesting a short,
    # representative snippet.
    words = [s.strip(".,;:!?") for s in s[:n*32].split(" ")]
    return " ".join(words[:n]) + ("…" if len(words) > n else "")

@dataclass
class Doc:
    id: str
    dolma_id: str
    text: str
    first_n: str
    source: str
    url: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Self:
        # TODO: common-crawl documents use the URL as an id; eventually some sort of post-processing
        # step will enrich each record with a URL (if there is one)
        url = None
        source = d["_source"]["source"]
        if source == "common-crawl":
            url = d["_source"]["id"]

        # TODO: we extract the first 8 words right now b/c there's no consistent title and/or
        # short representation
        text = d["_source"]["text"]
        first_n = first_n_words(text, 8)

        return cls(
            id=d["_id"],
            dolma_id=d["_source"]["id"],
            text=text,
            first_n=first_n,
            source=d["_source"]["source"],
            url=url,
        )

@dataclass
class Result(Doc):
    highlights: Mapping[str, list[HTML]] = field(default_factory=dict)
    score: float = 0.0

    @classmethod
    def from_hit(cls, hit: Mapping[str, Any]) -> Self:
        d = Doc.from_dict(hit)

        return cls(
            id=d.id,
            dolma_id=d.dolma_id,
            text=d.text,
            first_n=d.first_n,
            source=d.source,
            highlights=hit["highlight"],
            score=hit["_score"],
            url=d.url,
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
            timeout="30s", # return partial results after 30s
        )

        meta = SearchMeta(took_ms=res["took"], total=res["hits"]["total"]["value"],
                          overflow=res["hits"]["total"]["relation"] == "gte")
        results = [Result.from_hit(hit) for hit in res["hits"]["hits"]]

        return SearchResults(meta, results)

    def doc(self, id: str) -> Optional[Doc]:
        try:
            d = self.es.get(index="docs", id=id)
            return Doc.from_dict(d) # type: ignore
        except es8.exceptions.NotFoundError:
            return None

    def doc_count(self) -> int:
        stats = self.es.indices.stats(index="docs", metric=["docs"])
        return stats["_all"]["primaries"]["docs"]["count"]

