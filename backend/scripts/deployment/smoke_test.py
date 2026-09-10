#!/usr/bin/env python3
"""RSAI Production Smoke Test — PostgreSQL mode.

Usage:
    STORAGE_BACKEND=postgres DATABASE_URL=... python -m scripts.deployment.smoke_test
"""

import sys
import uuid
from datetime import UTC, datetime

import anyio

PASS = 0
FAIL = 0
ERRORS = []


def check(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        msg = f"{name}: {detail}" if detail else name
        ERRORS.append(msg)
        print(f"  ❌ {msg}")


async def run_smoke_tests():
    from app.db.database import create_engine, dispose_engine
    from app.models.application import Application, TimelineEvent
    from app.models.cover_letter import CoverLetter
    from app.models.interview import InterviewAnswer, InterviewQuestion, InterviewSession
    from app.models.match import MatchResult, Recommendation, SkillMatch
    from app.models.resume import Education, Experience, Resume
    from app.models.user import User
    from app.models.version import ResumeVersion
    from app.models.writer import ResumeSuggestion
    from app.services.repositories.factory import (
        get_application_repository,
        get_cover_letter_repository,
        get_interview_session_repository,
        get_match_repository,
        get_refresh_token_repository,
        get_resume_repository,
        get_suggestion_repository,
        get_timeline_event_repository,
        get_user_repository,
        get_version_repository,
    )

    engine = await create_engine()
    if engine is None:
        print("  ❌ Cannot connect to database")
        return False

    uid = uuid.uuid4().hex
    user_repo = get_user_repository()
    token_repo = get_refresh_token_repository()
    resume_repo = get_resume_repository()
    app_repo = get_application_repository()
    cl_repo = get_cover_letter_repository()
    match_repo = get_match_repository()
    ver_repo = get_version_repository()
    sug_repo = get_suggestion_repository()
    sess_repo = get_interview_session_repository()
    tl_repo = get_timeline_event_repository()

    # 1. User Registration
    user = User(
        id=uid,
        email=f"smoke.{uuid.uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$dummy",
        full_name="Smoke Test User",
    )
    user_repo.save(user)
    check("User registration", user_repo.get_by_id(uid) is not None)

    # 2. Login (simulated)
    loaded = user_repo.get_by_email(user.email)
    check("Email login lookup", loaded is not None and loaded.id == uid)
    loaded.last_login = datetime.now(UTC).isoformat()
    user_repo.save(loaded)
    check("Login timestamp update", user_repo.get_by_id(uid).last_login is not None)

    # 3. Resume creation
    rid = uuid.uuid4().hex
    resume = Resume(
        user_id=uid,
        full_name="Smoke Resume",
        email="smoke@test.com",
        summary="Professional software engineer",
        education=[Education(institution="MIT", degree="BS", field="CS")],
        experience=[Experience(company="Acme", title="Engineer", current=True)],
    )
    resume_repo.save(rid, resume)
    saved = resume_repo.get_by_id(rid)
    check("Resume creation", saved is not None and saved.full_name == "Smoke Resume")

    # 4. Resume update
    resume.full_name = "Smoke Resume Updated"
    resume_repo.save(rid, resume)
    check("Resume update", resume_repo.get_by_id(rid).full_name == "Smoke Resume Updated")

    # 5. Application creation
    aid = uuid.uuid4().hex
    app = Application(id=aid, user_id=uid, company="TestCorp", role_title="Backend Engineer")
    app_repo.save(app)
    check("Application creation", app_repo.get_by_id(aid) is not None)

    # 6. Application status update
    app.status = "applied"
    app_repo.save(app)
    check("Application status update", app_repo.get_by_id(aid).status.value == "applied")

    # 7. Application deletion + recreation
    app_repo.delete(aid)
    check("Application deletion", app_repo.get_by_id(aid) is None)
    app_repo.save(app)

    # 8. Timeline event
    te = TimelineEvent(id=uuid.uuid4().hex, application_id=aid, event_type="created", title="Application created")
    tl_repo.save(te)
    check("Timeline event creation", len(tl_repo.list_by_application(aid)) >= 1)

    # 9. Resume version
    ver = ResumeVersion(id=uuid.uuid4().hex, user_id=uid, resume_id=rid, label="v1", resume=resume)
    ver_repo.save(ver)
    check("Resume versioning", len(ver_repo.list_by_resume(rid)) >= 1)

    # 10. ATS Match generation
    mid = uuid.uuid4().hex
    match = MatchResult(
        id=mid,
        user_id=uid,
        resume_id=rid,
        job_title="Backend Engineer",
        overall_score=87.5,
        skill_matches=[SkillMatch(skill="Python", matched=True)],
        matched_skills=["Python", "SQL"],
        missing_skills=["Kubernetes"],
        recommendations=[Recommendation(section="Skills", message="Add Kubernetes experience", priority="high")],
        summary="Strong match",
    )
    match_repo.save(mid, match)
    check(
        "ATS Match creation", match_repo.get_by_id(mid) is not None and match_repo.get_by_id(mid).overall_score == 87.5
    )

    # 11. Cover letter generation
    clid = uuid.uuid4().hex
    letter = CoverLetter(
        id=clid,
        user_id=uid,
        resume_id=rid,
        company_name="TestCorp",
        role_title="Engineer",
        content="Dear Hiring Manager, I am writing to express my interest...",
        tone="professional",
    )
    cl_repo.save(letter)
    check("Cover letter generation", cl_repo.get_by_id(rid, clid) is not None)

    # 12. Interview session
    sid = uuid.uuid4().hex
    session = InterviewSession(
        id=sid,
        user_id=uid,
        application_id=aid,
        title="Technical Screen",
        session_type="mock",
    )
    sess_repo.save(session)
    check("Interview session creation", sess_repo.get_by_id(aid, sid) is not None)

    # 13. Interview questions
    qid = uuid.uuid4().hex
    q = InterviewQuestion(id=qid, session_id=sid, question_text="Describe your experience with Python")
    q_repo = __import__(
        "app.services.repositories.factory", fromlist=["get_interview_question_repository"]
    ).get_interview_question_repository()
    q_repo.save(q)
    check("Interview question generation", len(q_repo.list_by_session(sid)) >= 1)

    # 14. Interview answers
    a_repo = __import__(
        "app.services.repositories.factory", fromlist=["get_interview_answer_repository"]
    ).get_interview_answer_repository()
    answer = InterviewAnswer(id=uuid.uuid4().hex, question_id=qid, user_answer="I have 5 years of Python experience")
    a_repo.save(answer)
    check("Interview answer submission", a_repo.get_by_question(qid) is not None)

    # 15. Writer suggestions
    sugid = uuid.uuid4().hex
    sug = ResumeSuggestion(
        id=sugid,
        user_id=uid,
        resume_id=rid,
        section="summary",
        original_text="Old summary",
        suggested_text="New improved summary",
        confidence=0.95,
        status="pending",
    )
    sug_repo.save(sug)
    check("Writer suggestion creation", sug_repo.get_by_id(rid, sugid) is not None)

    sug_repo.update(rid, sugid, status="accepted")
    check("Writer suggestion accept", sug_repo.get_by_id(rid, sugid).status == "accepted")

    # 16. Logout
    token_repo.save("smoke_token", uid, "2026-12-31T23:59:59")
    token_repo.delete("smoke_token")
    check("Logout (token deletion)", token_repo.get_user_id("smoke_token") is None)

    # 17. Logout all
    token_repo.save("st1", uid, "2026-12-31T23:59:59")
    token_repo.save("st2", uid, "2026-12-31T23:59:59")
    token_repo.delete_all_for_user(uid)
    check("Logout all", token_repo.get_user_id("st1") is None and token_repo.get_user_id("st2") is None)

    await dispose_engine()
    return FAIL == 0


def main():
    print("=" * 56)
    print("  RSAI Production Smoke Tests")
    print("=" * 56)
    print("  Backend: postgres")
    print(f"  Time:    {datetime.now(UTC).isoformat()}")
    print()

    success = anyio.run(run_smoke_tests)

    print()
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print("=" * 56)

    if success:
        print("  ✅ ALL SMOKE TESTS PASSED")
        print("=" * 56)
        sys.exit(0)
    else:
        print("  ❌ SOME SMOKE TESTS FAILED")
        for err in ERRORS:
            print(f"     - {err}")
        print("=" * 56)
        sys.exit(1)


if __name__ == "__main__":
    main()
