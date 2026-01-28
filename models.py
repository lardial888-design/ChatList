from dataclasses import dataclass
from typing import List

import db


@dataclass
class ModelConfig:
    id: int
    name: str
    api_url: str
    api_key_env: str
    is_active: int


def get_active_models() -> List[ModelConfig]:
    rows = db.list_active_models()
    return [ModelConfig(**row) for row in rows]
