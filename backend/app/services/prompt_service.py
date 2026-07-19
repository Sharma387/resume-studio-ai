from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "prompts"


class PromptService:
    def __init__(self, prompts_dir: str | Path = PROMPTS_DIR):
        self._dir = Path(prompts_dir)

    def _load(self, name: str) -> str:
        path = self._dir / name
        return path.read_text(encoding="utf-8")

    def build_prompt(self, text: str, schema: str) -> tuple[str, str]:
        system = self._load("resume_parser_system.md")
        system = system.replace("{schema}", schema)
        user_template = self._load("resume_parser_user.md")
        user = user_template.replace("{text}", text).replace("{schema}", schema)
        return system, user
