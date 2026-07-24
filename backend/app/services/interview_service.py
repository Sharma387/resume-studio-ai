import json
import uuid
from datetime import datetime, timezone

from app.models.interview import (
    InterviewSession,
    InterviewQuestion,
    InterviewAnswer,
    ReadinessAssessment,
    SessionSummary,
    STARAttempt,
    QuestionType,
    Difficulty,
    AnswerType,
    SessionType,
)
from app.models.application import TimelineEvent, TimelineEventType
from app.services.repositories.factory import (
    get_resume_repository,
    get_application_repository,
    get_interview_session_repository,
    get_timeline_event_repository,
    get_match_repository,
    get_interview_question_repository,
    get_interview_answer_repository,
    get_readiness_assessment_repository,
    get_session_summary_repository,
)
from app.services.prompt_service import PromptService
from app.services.ai_core import call_with_retry, extract_json, AIServiceUnavailable

from app.core.logging import get_logger
logger = get_logger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _add_timeline(app_id: str, etype: TimelineEventType, title: str, desc: str = ""):
    event = TimelineEvent(id=uuid.uuid4().hex, application_id=app_id, event_type=etype, title=title, description=desc)
    get_timeline_event_repository().save(event)


def create_session(application_id: str, title: str, user_id: str, session_type: SessionType = SessionType.MOCK) -> InterviewSession:
    session = InterviewSession(id=uuid.uuid4().hex, user_id=user_id, application_id=application_id, title=title, session_type=session_type)
    get_interview_session_repository().save(session)
    _add_timeline(application_id, TimelineEventType.CREATED, f"Interview session created", title)
    return session


def get_session(application_id: str, session_id: str, user_id: str | None = None) -> InterviewSession | None:
    return get_interview_session_repository().get_by_id(application_id, session_id, user_id)


def list_sessions(application_id: str, user_id: str | None = None) -> list[InterviewSession]:
    return get_interview_session_repository().list_by_application(application_id, user_id)


def update_session(application_id: str, session_id: str, user_id: str | None = None, **kwargs) -> InterviewSession | None:
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
        _add_timeline(application_id, TimelineEventType.MOCK_INTERVIEW_COMPLETED, "Mock interview completed", session.title)
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

    async def build():
        return prompt_service.build_interview_questions_prompt(
            resume_json=resume_json, job_context=job_context, ats_gaps=ats_gaps, count=count,
        )

    def parse(raw: str) -> list[InterviewQuestion]:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        if not isinstance(data, list):
            data = [data]
        questions = []
        for item in data:
            q = InterviewQuestion(
                id=uuid.uuid4().hex,
                session_id=session_id,
                **{k: v for k, v in item.items() if k in InterviewQuestion.model_fields and k not in ("id", "session_id")},
            )
            get_interview_question_repository().save(q)
            questions.append(q)
        session = load_interview_session(application_id, session_id)
        if session:
            session.question_count = len(questions)
            session.updated_at = _now()
            get_interview_session_repository().save(session)
        return questions

    try:
        return await call_with_retry(build, parse, service_name="InterviewQuestions")
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

    async def build():
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
        coached = await call_with_retry(build, parse, service_name="AnswerCoach")
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

    async def build():
        return prompt_service.build_readiness_prompt(resume_json, job_context, "")

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
        return await call_with_retry(build, parse, service_name="Readiness")
    except AIServiceUnavailable as e:
        raise RuntimeError("Readiness assessment unavailable") from e


def list_readiness(application_id: str) -> list[ReadinessAssessment]:
    return get_readiness_assessment_repository().list_by_application(application_id)


async def generate_summary(session_id: str) -> SessionSummary:
    app_id = session_id.split("-")[0]
    questions = get_interview_question_repository().list_by_session(session_id)
    qa_pairs = []
    for q in questions:
        answer = _store.load_interview_answer(q.id)
        qa_pairs.append(f"Q: {q.question_text}\nA: {answer.user_answer if answer else '(unanswered)'}")

    prompt_service = PromptService()

    async def build():
        return prompt_service.build_interview_summary_prompt("\n\n".join(qa_pairs))

    def parse(raw: str) -> SessionSummary:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        summary = SessionSummary(
            id=uuid.uuid4().hex,
            session_id=session_id,
            application_id=app_id,
            total_questions=len(questions),
            answered_questions=sum(1 for _ in questions if _store.load_interview_answer(_.id)),
            strengths=data.get("strengths", []),
            areas_to_improve=data.get("areas_to_improve", []),
            recommendations=data.get("recommendations", []),
        )
        get_session_summary_repository().save(summary)
        return summary

    try:
        return await call_with_retry(build, parse, service_name="SessionSummary")
    except AIServiceUnavailable as e:
        raise RuntimeError("Summary generation unavailable") from e
