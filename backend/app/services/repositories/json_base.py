"""Generic JSON implementation of BaseRepository."""

import json
from pathlib import Path
from typing import Generic

from pydantic import BaseModel

from app.core.config import settings
from app.services.repositories.interfaces import BaseRepository, T


class JsonBaseRepository(BaseRepository[T], Generic[T]):
    """JSON file-based repository for any Pydantic model.

    Subclasses only need to set model_class and sub_dir.
    """

    model_class: type[T]
    sub_dir: str = ""

    def __init__(self) -> None:
        self.root = settings.storage_path / self.sub_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, entity_id: str) -> Path:
        return self.root / f"{entity_id}.json"

    def save(self, entity_id: str, entity: T) -> None:
        path = self._path(entity_id)
        path.write_text(entity.model_dump_json(indent=2), encoding="utf-8")

    def get(self, entity_id: str) -> T | None:
        path = self._path(entity_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return self.model_class(**data)

    def delete(self, entity_id: str) -> bool:
        path = self._path(entity_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_all(self) -> list[T]:
        if not self.root.exists():
            return []
        results = []
        for f in self.root.iterdir():
            if f.suffix == ".json":
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append(self.model_class(**data))
        return results

    def list_by_field(self, field: str, value: str) -> list[T]:
        return [e for e in self.list_all() if getattr(e, field, None) == value]
