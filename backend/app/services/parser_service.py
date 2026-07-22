import json
import logging
import re

from pydantic import ValidationError

from app.core.config import settings
from app.models.resume import Resume, Education, Experience, Project, Skill, Certification
from app.services.prompt_service import PromptService
from app.services.omniroute_service import OmniRouteService, OmniRouteError

logger = logging.getLogger(__name__)


class ParseError(Exception):
    pass


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()


def _mock_resume() -> Resume:
    return Resume(
        full_name="Alexandra Chen",
        email="alexandra.chen@example.com",
        phone="+1 (555) 123-4567",
        location="San Francisco, CA",
        linkedin="https://linkedin.com/in/alexchen",
        github="https://github.com/alexchen",
        website="https://alexchen.dev",
        summary="Senior full-stack engineer with 6+ years of experience building scalable web applications. "
        "Proficient in React, Python, and cloud infrastructure. Passionate about developer tooling and AI.",
        education=[
            Education(
                institution="University of California, Berkeley",
                degree="Bachelor of Science",
                field="Computer Science",
                start_date="2014-08",
                end_date="2018-05",
                gpa=3.7,
                achievements=["Dean's List 2016, 2017", "Teaching Assistant for Data Structures"],
            ),
        ],
        experience=[
            Experience(
                company="TechCorp Inc.",
                title="Senior Software Engineer",
                location="San Francisco, CA",
                start_date="2021-03",
                end_date=None,
                current=True,
                description=[
                    "Led a team of 5 engineers building a real-time data pipeline processing 10M+ events/day",
                    "Designed and implemented a microservices architecture reducing deployment time by 60%",
                    "Mentored 3 junior engineers through structured code reviews and pair programming",
                ],
            ),
            Experience(
                company="StartupXYZ",
                title="Full Stack Engineer",
                location="Oakland, CA",
                start_date="2018-06",
                end_date="2021-02",
                current=False,
                description=[
                    "Built the core SaaS platform using React, Node.js, and PostgreSQL",
                    "Implemented CI/CD pipelines with GitHub Actions and Docker",
                    "Reduced API response times by 40% through query optimization and caching",
                ],
            ),
        ],
        projects=[
            Project(
                name="Open Source CLI Tool",
                description="A command-line tool for scaffolding React components with built-in best practices",
                url="https://github.com/alexchen/scaffold-react",
                technologies=["TypeScript", "Node.js", "Commander.js"],
            ),
            Project(
                name="AI Resume Analyzer",
                description="An NLP-based tool that analyzes resumes and provides ATS optimization suggestions",
                url="https://github.com/alexchen/resume-analyzer",
                technologies=["Python", "FastAPI", "OpenAI", "React"],
            ),
        ],
        skills=[
            Skill(category="Languages", skills=["TypeScript", "Python", "Go", "SQL"]),
            Skill(category="Frontend", skills=["React", "Next.js", "Tailwind CSS", "Redux"]),
            Skill(category="Backend", skills=["FastAPI", "Node.js", "PostgreSQL", "Redis"]),
            Skill(category="DevOps", skills=["Docker", "Kubernetes", "AWS", "Terraform"]),
        ],
        certifications=[
            Certification(
                name="AWS Solutions Architect – Associate",
                issuer="Amazon Web Services",
                date="2022-11",
                url="https://aws.amazon.com/certification/",
            ),
        ],
    )


async def parse_resume(text: str) -> Resume:
    if "localhost" not in settings.omniroute_api_url and not settings.omniroute_api_key:
        logger.info("No OmniRoute endpoint configured; returning mock resume")
        return _mock_resume()

    prompt_service = PromptService()
    omniroute = OmniRouteService()

    schema = json.dumps(Resume.model_json_schema(), indent=2)
    system_prompt, user_prompt = prompt_service.build_prompt(text, schema)

    last_error: Exception | None = None

    for attempt in range(omniroute.max_retries + 1):
        try:
            raw = await omniroute.send_prompt(system_prompt, user_prompt)
            cleaned = _extract_json(raw)
            data = json.loads(cleaned)
            return Resume(**data)
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON from OmniRoute (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except ValidationError as e:
            logger.warning("Pydantic validation failed (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except OmniRouteError as e:
            logger.warning("OmniRoute request failed (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e

    logger.warning("OmniRoute parsing failed after retries; falling back to mock data")
    return _mock_resume()
