import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.models.interview import (
    InterviewSession, InterviewQuestion, InterviewAnswer, ReadinessAssessment,
    SessionSummary, STARAttempt, QuestionType, Difficulty, AnswerType, SessionType,
)
from app.models.application import TimelineEventType
from app.services import interview_service as svc
from app.services.storage_service import save_application, save_timeline_event
from app.models.application import Application


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def app_id():
    aid = "int-app-1"
    save_application(Application(user_id="test", id=aid, company="Acme", role_title="Engineer"))
    return aid


class TestInterviewModels:
    def test_session_defaults(self):
        s = InterviewSession(user_id="test", id="s1", application_id="a1")
        assert s.session_type == SessionType.MOCK
        assert s.completed is False

    def test_session_with_plan_id(self):
        s = InterviewSession(user_id="test", id="s2", application_id="a1", plan_id="plan-1")
        assert s.plan_id == "plan-1"

    def test_question_defaults(self):
        q = InterviewQuestion(id="q1", session_id="s1", question_text="Tell me about yourself")
        assert q.difficulty == Difficulty.MEDIUM
        assert q.question_type == QuestionType.BEHAVIORAL

    def test_difficulty_enum(self):
        q = InterviewQuestion(id="q2", session_id="s1", question_text="Q", difficulty=Difficulty.HARD)
        assert q.difficulty == Difficulty.HARD

    def test_question_tags(self):
        q = InterviewQuestion(id="q3", session_id="s1", question_text="Q", tags=["leadership", "teamwork"])
        assert len(q.tags) == 2

    def test_invalid_difficulty(self):
        with pytest.raises(ValidationError):
            InterviewQuestion(id="q4", session_id="s1", question_text="Q", difficulty="expert")

    def test_answer_defaults(self):
        a = InterviewAnswer(id="a1", question_id="q1")
        assert a.answer_type == AnswerType.TEXT

    def test_star_attempt_defaults(self):
        star = STARAttempt()
        assert star.situation is None
        assert star.task is None

    def test_readiness_score_range(self):
        with pytest.raises(ValidationError):
            ReadinessAssessment(id="r1", application_id="a1", overall_score=150)

    def test_session_summary(self):
        s = SessionSummary(id="sum1", session_id="s1", application_id="a1")
        assert s.total_questions == 0

    def test_mock_interview_completed_type(self):
        assert TimelineEventType.MOCK_INTERVIEW_COMPLETED == "mock_interview_completed"


class TestInterviewService:
    def test_create_session(self, app_id):
        s = svc.create_session(app_id, "Google Phone Screen", "test")
        assert s.application_id == app_id
        assert s.title == "Google Phone Screen"

    def test_list_sessions(self, app_id):
        svc.create_session(app_id, "S1", "test")
        sessions = svc.list_sessions(app_id)
        assert len(sessions) >= 1

    def test_get_session_not_found(self, app_id):
        assert svc.get_session(app_id, "nonexistent") is None

    def test_update_session(self, app_id):
        s = svc.create_session(app_id, "Original", "test")
        updated = svc.update_session(app_id, s.id, title="Updated")
        assert updated.title == "Updated"

    def test_complete_session(self, app_id):
        s = svc.create_session(app_id, "Test", "test")
        completed = svc.complete_session(app_id, s.id)
        assert completed.completed is True

    def test_delete_session(self, app_id):
        s = svc.create_session(app_id, "Delete me", "test")
        assert svc.delete_session(app_id, s.id) is True
        assert svc.get_session(app_id, s.id) is None

    def test_submit_answer(self):
        import asyncio
        answer = asyncio.run(svc.submit_answer("q-test-1", "I led a team..."))
        assert answer.user_answer == "I led a team..."
        assert answer.answer_type == AnswerType.TEXT


class TestEndpoints:
    @pytest.mark.asyncio
    async def test_create_session(self, client, app_id):
        async with client as ac:
            resp = await ac.post(f"/api/v1/applications/{app_id}/interview/sessions", json={"id": "es1", "user_id": "test", "application_id": app_id, "title": "Prep"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Prep"

    @pytest.mark.asyncio
    async def test_list_sessions(self, client, app_id):
        async with client as ac:
            resp = await ac.get(f"/api/v1/applications/{app_id}/interview/sessions")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, client, app_id):
        async with client as ac:
            resp = await ac.get(f"/api/v1/applications/{app_id}/interview/sessions/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session(self, client, app_id):
        s = svc.create_session(app_id, "Del", "test")
        async with client as ac:
            resp = await ac.delete(f"/api/v1/applications/{app_id}/interview/sessions/{s.id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_session(self, client, app_id):
        s = svc.create_session(app_id, "Complete", "test")
        async with client as ac:
            resp = await ac.post(f"/api/v1/applications/{app_id}/interview/sessions/{s.id}/complete")
        assert resp.status_code == 200
        assert resp.json()["data"]["completed"] is True
