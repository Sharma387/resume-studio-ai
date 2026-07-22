from fastapi import APIRouter, HTTPException

from app.models.interview import InterviewSession, SessionType
from app.services import interview_service as svc

router = APIRouter()


@router.post("/applications/{app_id}/interview/sessions")
async def create_session(app_id: str, body: InterviewSession):
    session = svc.create_session(app_id, body.title or "Interview Prep", body.session_type)
    return {"success": True, "data": session}


@router.get("/applications/{app_id}/interview/sessions")
async def list_sessions(app_id: str):
    sessions = svc.list_sessions(app_id)
    return {"success": True, "data": [s.model_dump() for s in sessions]}


@router.get("/applications/{app_id}/interview/sessions/{session_id}")
async def get_session(app_id: str, session_id: str):
    session = svc.get_session(app_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "data": session}


@router.put("/applications/{app_id}/interview/sessions/{session_id}")
async def update_session(app_id: str, session_id: str, body: InterviewSession):
    updated = svc.update_session(app_id, session_id, **body.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "data": updated}


@router.delete("/applications/{app_id}/interview/sessions/{session_id}")
async def delete_session(app_id: str, session_id: str):
    if not svc.delete_session(app_id, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


@router.post("/applications/{app_id}/interview/sessions/{session_id}/complete")
async def complete_session(app_id: str, session_id: str):
    session = svc.complete_session(app_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "data": session}


@router.post("/applications/{app_id}/interview/sessions/{session_id}/generate-questions")
async def generate_questions(app_id: str, session_id: str, count: int = 5):
    try:
        questions = await svc.generate_questions(app_id, session_id, count)
        return {"success": True, "data": [q.model_dump() for q in questions]}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/applications/{app_id}/interview/sessions/{session_id}/questions")
async def list_questions(app_id: str, session_id: str):
    questions = svc.list_questions(session_id)
    return {"success": True, "data": [q.model_dump() for q in questions]}


@router.post("/applications/{app_id}/interview/questions/{question_id}/answer")
async def submit_answer(app_id: str, question_id: str, body: dict):
    question_text = body.get("question_text", "")
    user_answer = body.get("user_answer", "")
    if not user_answer:
        raise HTTPException(status_code=400, detail="user_answer is required")

    if question_text:
        coached = await svc.coach_answer(question_id, question_text, user_answer)
    else:
        coached = await svc.submit_answer(question_id, user_answer)
    return {"success": True, "data": coached}


@router.get("/applications/{app_id}/interview/questions/{question_id}/answer")
async def get_answer(app_id: str, question_id: str):
    answer = svc.get_answer(question_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    return {"success": True, "data": answer}


@router.post("/applications/{app_id}/interview/assess-readiness")
async def assess_readiness(app_id: str):
    try:
        assessment = await svc.assess_readiness(app_id)
        return {"success": True, "data": assessment}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/applications/{app_id}/interview/readiness")
async def list_readiness(app_id: str):
    assessments = svc.list_readiness(app_id)
    return {"success": True, "data": [a.model_dump() for a in assessments]}


@router.post("/applications/{app_id}/interview/sessions/{session_id}/summary")
async def generate_summary(app_id: str, session_id: str):
    try:
        summary = await svc.generate_summary(session_id)
        return {"success": True, "data": summary}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/applications/{app_id}/interview/sessions/{session_id}/summary")
async def get_summary(app_id: str, session_id: str):
    from app.services.storage_service import load_session_summary
    summary = load_session_summary(session_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary not found")
    return {"success": True, "data": summary}
