import json
from pathlib import Path

from app.models.resume import Resume

STORAGE_DIR = Path("storage") / "resumes"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_resume(resume_id: str, resume: Resume) -> None:
    path = STORAGE_DIR / f"{resume_id}.json"
    path.write_text(resume.model_dump_json(indent=2), encoding="utf-8")


def load_resume(resume_id: str) -> Resume | None:
    path = STORAGE_DIR / f"{resume_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Resume(**data)
