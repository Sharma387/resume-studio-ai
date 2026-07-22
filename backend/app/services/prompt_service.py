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

    def build_cover_letter_prompt(
        self,
        resume_json: str,
        job_description: str,
        company_name: str | None = None,
        role_title: str | None = None,
        hiring_manager: str | None = None,
        tone: str = "professional",
    ) -> tuple[str, str]:
        system = self._load("cover_letter_system.md")
        system = system.replace("{tone}", tone)
        user_template = self._load("cover_letter_user.md")
        user = user_template.replace("{resume_json}", resume_json)
        user = user.replace("{job_description}", job_description)
        user = user.replace("{company_name}", company_name or "the company")
        user = user.replace("{role_title}", role_title or "the position")
        user = user.replace("{hiring_manager}", hiring_manager or "Hiring Manager")
        user = user.replace("{tone}", tone)
        return system, user

    def build_interview_questions_prompt(
        self,
        resume_json: str,
        job_context: str,
        ats_gaps: str = "",
        focus_areas: str = "",
        count: int = 5,
    ) -> tuple[str, str]:
        system = self._load("interview_questions_system.md")
        user_template = self._load("interview_questions_user.md")
        user = user_template.replace("{resume_json}", resume_json)
        user = user.replace("{job_context}", job_context or "N/A")
        user = user.replace("{ats_gaps}", ats_gaps or "None identified")
        user = user.replace("{focus_areas}", focus_areas or "General")
        user = user.replace("{count}", str(count))
        return system, user

    def build_answer_coach_prompt(self, question: str, answer: str) -> tuple[str, str]:
        system = self._load("interview_answer_coach_system.md")
        user = f"Question: {question}\n\nCandidate's Answer:\n{answer}\n\nProvide STAR coaching."
        return system, user

    def build_readiness_prompt(self, resume_json: str, job_context: str, answers_summary: str) -> tuple[str, str]:
        system = self._load("interview_readiness_system.md")
        user = f"Resume:\n{resume_json}\n\nJob Context:\n{job_context}\n\nAnswers Provided:\n{answers_summary}\n\nAssess readiness."
        return system, user

    def build_interview_summary_prompt(self, questions_and_answers: str) -> tuple[str, str]:
        system = self._load("interview_summary_system.md")
        user = f"Session Data:\n{questions_and_answers}\n\nGenerate summary."
        return system, user
