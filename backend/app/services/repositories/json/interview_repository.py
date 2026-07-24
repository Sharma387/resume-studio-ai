from app.models.interview import InterviewSession, InterviewQuestion, InterviewAnswer, ReadinessAssessment, SessionSummary
from app.services.repositories.interfaces import InterviewSessionRepository, InterviewQuestionRepository, InterviewAnswerRepository, ReadinessAssessmentRepository, SessionSummaryRepository
from app.services.repositories.interfaces import InterviewSessionRepository
from app.services import storage_service as store


class JsonInterviewSessionRepository(InterviewSessionRepository):
    def save(self, session: InterviewSession) -> None:
        store.save_interview_session(session)

    def get_by_id(self, application_id: str, session_id: str, user_id: str | None = None) -> InterviewSession | None:
        return store.load_interview_session(application_id, session_id, user_id)

    def list_by_application(self, application_id: str, user_id: str | None = None) -> list[InterviewSession]:
        return store.list_interview_sessions(application_id, user_id)

    def delete(self, application_id: str, session_id: str) -> bool:
        return store.delete_interview_session(application_id, session_id)


class JsonInterviewQuestionRepository(InterviewQuestionRepository):
    def save(self, question: InterviewQuestion) -> None:
        store.save_interview_question(question)

    def list_by_session(self, session_id: str) -> list[InterviewQuestion]:
        return store.list_interview_questions(session_id)


class JsonInterviewAnswerRepository(InterviewAnswerRepository):
    def save(self, answer: InterviewAnswer) -> None:
        store.save_interview_answer(answer)

    def get_by_question(self, question_id: str) -> InterviewAnswer | None:
        return store.load_interview_answer(question_id)


class JsonReadinessAssessmentRepository(ReadinessAssessmentRepository):
    def save(self, assessment: ReadinessAssessment) -> None:
        store.save_readiness_assessment(assessment)

    def list_by_application(self, application_id: str) -> list[ReadinessAssessment]:
        return store.list_readiness_assessments(application_id)


class JsonSessionSummaryRepository(SessionSummaryRepository):
    def save(self, summary: SessionSummary) -> None:
        store.save_session_summary(summary)

    def get_by_session(self, session_id: str) -> SessionSummary | None:
        return store.load_session_summary(session_id)
