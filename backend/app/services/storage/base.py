"""Base storage class with common file operations."""

import json
from pathlib import Path


class BaseStorage:
    """Generic JSON file storage with path management."""

    def __init__(self, base_dir: Path | str, sub_dir: str = ""):
        self.root = Path(base_dir)
        if sub_dir:
            self.root = self.root / sub_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str, *parts: str) -> Path:
        path = self.root
        for p in [key, *parts]:
            path = path / p
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, key: str, data: dict, *parts: str) -> None:
        path = self._path(key, *parts)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def load(self, key: str, *parts: str) -> dict | None:
        path = self._path(key, *parts)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def delete(self, key: str, *parts: str) -> bool:
        path = self._path(key, *parts)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_all(self, subdir: str = "") -> list[Path]:
        path = self.root / subdir if subdir else self.root
        if not path.exists():
            return []
        return sorted([f for f in path.iterdir() if f.suffix == ".json"], reverse=True)
