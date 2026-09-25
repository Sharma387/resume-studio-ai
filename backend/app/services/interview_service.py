import json
import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from app.core.logging import get_logger
from app.models.application import TimelineEvent, TimelineEventType
from app.models.interview import (
    InterviewAnswer,
    InterviewQuestion,
    InterviewSession,
    ReadinessAssessment,
    SessionSummary,
    SessionType,
    STARAttempt,
)
from app.services.ai_core import AIServiceUnavailable, extract_json, extract_json_array
from app.services.ollama_service import compact_resume, run_with_providers
from app.services.prompt_service import PromptService
from app.services.repositories.factory import (
    get_application_repository,
    get_interview_answer_repository,
    get_interview_question_repository,
    get_interview_session_repository,
    get_match_repository,
    get_readiness_assessment_repository,
    get_resume_repository,
    get_session_summary_repository,
    get_timeline_event_repository,
)

logger = get_logger(__name__)

INTERVIEW_QUESTIONS_SYSTEM_PROMPT = """You are an interview coach generating tailored interview questions. Return ONLY a JSON array of question objects with fields:
- question_type: "behavioral", "technical", "situational", "role_specific", or "culture_fit"
- question_text: string (the full question)
- focus_area: string or null (e.g. "leadership", "cloud architecture")
- tips: [string] — brief advice for answering well
- tags: [string] — short subject tags
- difficulty: "easy", "medium", or "hard"

Do not include id or session_id — the backend manages those. Use lowercase null."""

READINESS_SYSTEM_PROMPT = """You are an interview readiness assessor. Analyse the candidate's resume against the target role and return ONLY a JSON object with:
- overall_score: number from 0 to 100
- category_scores: object of category → score (0-100), e.g. {"technical": 80, "behavioral": 65}
- strengths: [string]
- weaknesses: [string]
- recommendations: [string]

Use lowercase null. Keep every list item concise."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _add_timeline(app_id: str, etype: TimelineEventType, title: str, desc: str = ""):
    event = TimelineEvent(id=uuid.uuid4().hex, application_id=app_id, event_type=etype, title=title, description=desc)
    get_timeline_event_repository().save(event)


def create_session(
    application_id: str, title: str, user_id: str, session_type: SessionType = SessionType.MOCK
) -> InterviewSession:
    session = InterviewSession(
        id=uuid.uuid4().hex, user_id=user_id, application_id=application_id, title=title, session_type=session_type
    )
    get_interview_session_repository().save(session)
    _add_timeline(application_id, TimelineEventType.CREATED, "Interview session created", title)
    return session


def get_session(application_id: str, session_id: str, user_id: str | None = None) -> InterviewSession | None:
    return get_interview_session_repository().get_by_id(application_id, session_id, user_id)


def list_sessions(application_id: str, user_id: str | None = None) -> list[InterviewSession]:
    return get_interview_session_repository().list_by_application(application_id, user_id)


def update_session(
    application_id: str, session_id: str, user_id: str | None = None, **kwargs
) -> InterviewSession | None:
    session = get_interview_session_repository().get_by_id(application_id, session_id, user_id)
    if session is None:
        return None
    for key, value in kwargs.items():
        if key in InterviewSession.model_fields and key not in ("id", "application_id", "created_at"):
            setattr(session, key, value)
    session.updated_at = _now()
    get_interview_session_repository().save(session)
    return session


def delete_session(application_id: str, session_id: str, user_id: str | None = None) -> bool:
    return get_interview_session_repository().delete(application_id, session_id)


def complete_session(application_id: str, session_id: str) -> InterviewSession | None:
    session = update_session(application_id, session_id, completed=True)
    if session:
        _add_timeline(
            application_id, TimelineEventType.MOCK_INTERVIEW_COMPLETED, "Mock interview completed", session.title
        )
    return session


async def generate_questions(application_id: str, session_id: str, count: int = 5) -> list[InterviewQuestion]:
    app = get_application_repository().get_by_id(application_id)
    if app is None:
        raise FileNotFoundError("Application not found")
    resume = get_resume_repository().get_by_id(app.resume_id) if app.resume_id else None
    resume_json = json.dumps(resume.model_dump(), indent=2, default=str) if resume else "{}"
    matches = get_match_repository().list_by_resume(app.resume_id) if app.resume_id else []
    ats_gaps = ", ".join(matches[0].missing_skills) if matches else ""

    job_context = f"{app.role_title} at {app.company}" if app.company else "N/A"

    prompt_service = PromptService()

    async def build_omniroute_prompt():
        return prompt_service.build_interview_questions_prompt(
            resume_json=resume_json,
            job_context=job_context,
            ats_gaps=ats_gaps,
            count=count,
        )

    async def build_ollama_prompt():
        user_prompt = (
            f"Candidate resume (JSON):\n{compact_resume(resume) if resume else '{}'}\n\n"
            f"Target role: {job_context}\n"
            f"ATS skill gaps to probe: {ats_gaps or 'none'}\n"
            f"Number of questions: {count}"
        )
        return INTERVIEW_QUESTIONS_SYSTEM_PROMPT, user_prompt

    def parse(raw: str) -> list[InterviewQuestion]:
        # Output is a JSON ARRAY of questions; extract_json_array keeps the
        # brackets (object-mode extract_json would return {..},{..} → "Extra data").
        cleaned = extract_json_array(raw)
        data = json.loads(cleaned)
        if not isinstance(data, list):
            data = [data]
        questions = []
        for item in data:
            try:
                q = InterviewQuestion(
                    id=uuid.uuid4().hex,
                    session_id=session_id,
                    **{
                        k: v
                        for k, v in item.items()
                        if k in InterviewQuestion.model_fields and k not in ("id", "session_id")
                    },
                )
            except ValidationError as e:
                logger.warning("Skipping invalid interview question: %s", e)
                continue
            get_interview_question_repository().save(q)
            questions.append(q)
        if not questions:
            # Nothing usable from the model — let the dispatcher try the next provider.
            raise ValueError("no valid interview questions in model output")
        session = get_interview_session_repository().get_by_id(application_id, session_id)
        if session:
            session.question_count = len(questions)
            session.updated_at = _now()
            get_interview_session_repository().save(session)
        return questions

    try:
        return await run_with_providers(
            service_name="InterviewQuestions",
            build_ollama_prompt=build_ollama_prompt,
            build_omniroute_prompt=build_omniroute_prompt,
            parse=parse,
            allow_mock=False,
        )
    except AIServiceUnavailable as e:
        raise RuntimeError("Question generation unavailable") from e


def list_questions(session_id: str) -> list[InterviewQuestion]:
    return get_interview_question_repository().list_by_session(session_id)


async def submit_answer(question_id: str, user_answer: str) -> InterviewAnswer:
    answer = InterviewAnswer(id=uuid.uuid4().hex, question_id=question_id, user_answer=user_answer)
    get_interview_answer_repository().save(answer)
    return answer


async def coach_answer(question_id: str, question_text: str, user_answer: str) -> InterviewAnswer:
    prompt_service = PromptService()

    async def build_hint() -> tuple[str, str]:
        return prompt_service.build_answer_coach_prompt(question_text, user_answer)

    def parse(raw: str) -> InterviewAnswer:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        star = data.get("star_attempt", {})
        return InterviewAnswer(
            id=uuid.uuid4().hex,
            question_id=question_id,
            user_answer=user_answer,
            star_attempt=STARAttempt(**star),
            feedback=data.get("feedback"),
            improved_answer=data.get("improved_answer"),
            score=data.get("score"),
        )

    try:
        coached = await run_with_providers(
            service_name="AnswerCoach",
            build_ollama_prompt=build_hint,  # prompt is small; fine for local models
            build_omniroute_prompt=build_hint,
            parse=parse,
            allow_mock=False,
        )
        get_interview_answer_repository().save(coached)
        return coached
    except AIServiceUnavailable as e:
        raise RuntimeError("Answer coaching unavailable") from e


def get_answer(question_id: str) -> InterviewAnswer | None:
    return get_interview_answer_repository().get_by_question(question_id)


async def assess_readiness(application_id: str) -> ReadinessAssessment:
    app = get_application_repository().get_by_id(application_id)
    if app is None:
        raise FileNotFoundError("Application not found")
    resume = get_resume_repository().get_by_id(app.resume_id) if app.resume_id else None
    resume_json = json.dumps(resume.model_dump(), indent=2, default=str) if resume else "{}"
    job_context = f"{app.role_title} at {app.company}" if app.company else "N/A"

    prompt_service = PromptService()

    async def build_omniroute_prompt():
        return prompt_service.build_readiness_prompt(resume_json, job_context, "")

    async def build_ollama_prompt():
        user_prompt = (
            f"Candidate resume (JSON):\n{compact_resume(resume) if resume else '{}'}\n\n"
            f"Target role: {job_context}"
        )
        return READINESS_SYSTEM_PROMPT, user_prompt

    def parse(raw: str) -> ReadinessAssessment:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        assessment = ReadinessAssessment(
            id=uuid.uuid4().hex,
            application_id=application_id,
            overall_score=data.get("overall_score", 50),
            category_scores=data.get("category_scores", {}),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            recommendations=data.get("recommendations", []),
        )
        get_readiness_assessment_repository().save(assessment)
        return assessment

    try:
        return await run_with_providers(
            service_name="Readiness",
            build_ollama_prompt=build_ollama_prompt,
            build_omniroute_prompt=build_omniroute_prompt,
            parse=parse,
            allow_mock=False,
        )
    except AIServiceUnavailable as e:
        raise RuntimeError("Readiness assessment unavailable") from e


def list_readiness(application_id: str) -> list[ReadinessAssessment]:
    return get_readiness_assessment_repository().list_by_application(application_id)


async def generate_summary(session_id: str, application_id: str | None = None) -> SessionSummary:
    # Session ids are bare hex (not "<application_id>-<random>"), so the app id
    # must come from the caller; keep the split as a fallback for safety.
    app_id = application_id or session_id.split("-")[0]
    questions = get_interview_question_repository().list_by_session(session_id)
    qa_pairs = []
    for q in questions:
        answer = get_interview_answer_repository().get_by_question(q.id)
        qa_pairs.append(f"Q: {q.question_text}\nA: {answer.user_answer if answer else '(unanswered)'}")

    prompt_service = PromptService()

    async def build_summary() -> tuple[str, str]:
        return prompt_service.build_interview_summary_prompt("\n\n".join(qa_pairs))

    def parse(raw: str) -> SessionSummary:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        summary = SessionSummary(
            id=uuid.uuid4().hex,
            session_id=session_id,
            application_id=app_id,
            total_questions=len(questions),
            answered_questions=sum(1 for _ in questions if get_interview_answer_repository().get_by_question(_.id)),
            strengths=data.get("strengths", []),
            areas_to_improve=data.get("areas_to_improve", []),
            recommendations=data.get("recommendations", []),
        )
        get_session_summary_repository().save(summary)
        return summary

    try:
        return await run_with_providers(
            service_name="SessionSummary",
            build_ollama_prompt=build_summary,  # QA transcript prompt; small enough for local models
            build_omniroute_prompt=build_summary,
            parse=parse,
            allow_mock=False,
        )
    except AIServiceUnavailable as e:
        raise RuntimeError("Summary generation unavailable") from e
