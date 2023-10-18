from typing import Self
from dataclasses import dataclass

import json

@dataclass
class Database:
    conninfo: str
    min_size: int = 1
    max_size: int = 2

@dataclass
class Elastic:
    endpoint: str
    api_key: str

@dataclass
class InferD:
    address: str

@dataclass
class Server:
    num_proxies: int
    log_level: str
    admins: list[str]
    api_origin: str
    ui_origin: str
    # Origins (http://<host>:<port>) that we're allowed to redirect clients to after authentication.
    # The ui_origin is automatically included.
    allowed_redirects: list[str]

@dataclass
class Config:
    db: Database
    es: Elastic
    inferd: InferD
    server: Server

    @classmethod
    def load(cls, path: str = "/secret/cfg/config.json") -> Self:
        with open(path) as f:
            data = json.load(f)
            return cls(
                db=Database(**data["db"]),
                es=Elastic(**data["es"]),
                inferd=InferD(**data["inferd"]),
                server=Server(
                    data["server"]["num_proxies"],
                    data["server"].get("log_level", "INFO"),
                    data["server"].get("admins", []),
                    data["server"].get("origin", "http://localhost:8000"),
                    data["server"].get("ui_origin", "http://localhost:8080"),
                    data["server"].get("allowed_redirects", []),
                ),
            )

