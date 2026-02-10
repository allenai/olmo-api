from dataclasses import dataclass


@dataclass(kw_only=True)
class InfiniGramSource:
    name: str
    usage: str
    display_name: str | None = None
    secondary_name: str | None = None
    url: str | None = None

    def __post_init__(self):
        self.display_name = self.display_name or self.name
        self.url = self.url or f"https://huggingface.co/datasets/allenai/{self.name}"


class InfiGramSourceList(dict[str, InfiniGramSource]):
    def __init__(self, *sources: InfiniGramSource):
        mapped_sources: dict[str, InfiniGramSource] = {}
        for infini_gram_source in sources:
            mapped_sources[infini_gram_source.name] = infini_gram_source

        super().__init__(mapped_sources)
