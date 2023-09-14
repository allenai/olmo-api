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

@dataclass
class Config:
    db: Database
    es: Elastic
    inferd: InferD
    server: Server
    log_level: str = "INFO"

    @classmethod
    def load(cls, path: str = "/secret/cfg/config.json") -> Self:
        with open(path) as f:
            data = json.load(f)
            return cls(
                db=Database(**data["db"]),
                es=Elastic(**data["es"]),
                inferd=InferD(**data["inferd"]),
                server=Server(**data["server"]),
            )

