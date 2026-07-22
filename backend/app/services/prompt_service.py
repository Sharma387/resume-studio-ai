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

    def build_match_prompt(self, resume_json: str, job_description: str, match_schema: str) -> tuple[str, str]:
        system = self._load("resume_matcher_system.md")
        user_template = self._load("resume_matcher_user.md")
        user = user_template.replace("{resume_json}", resume_json).replace("{job_description}", job_description).replace("{match_schema}", match_schema)
        return system, user

    def build_writer_prompt(self, resume_json: str, user_prompt: str, focus_section: str | None = None) -> tuple[str, str]:
        system = self._load("resume_writer_system.md")
        user_template = self._load("resume_writer_user.md")
        user = user_template.replace("{resume_json}", resume_json).replace("{user_prompt}", user_prompt)
        user = user.replace("{focus_section}", focus_section or "null")
        return system, user
