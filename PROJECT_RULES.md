# PROJECT_RULES.md

# Simple_Resume – AI Engineering Constitution

## Vision
Build a production-quality AI Resume Parser that:
- Accepts PDF resumes.
- Uses OmniRoute for AI inference.
- Extracts structured resume data.
- Generates a standardized resume matching the chosen template.
- Provides a modern React UI.
- Runs automated tests and fixes issues before marking work complete.

## Tech Stack
- Backend: FastAPI, Python
- Frontend: React + TypeScript + Vite + Material UI
- AI: OmniRoute
- Testing: Pytest, Vitest, Playwright

## Architecture
Frontend → FastAPI → AI Service → OmniRoute → JSON → Resume Renderer

## Coding Standards
- Keep code modular.
- Use type hints.
- Never hardcode secrets.
- Log meaningful errors.
- Business logic belongs in services.
- API endpoints remain thin.

## Folder Structure
```
backend/
frontend/
docs/
prompts/
tests/
```

## Definition of Done
A task is complete only if:
1. Code builds.
2. Lint passes.
3. Unit tests pass.
4. Integration tests pass.
5. End-to-end tests pass.
6. Documentation updated.

## Initial Milestones
1. Scaffold FastAPI backend.
2. Scaffold React frontend.
3. Connect frontend and backend.
4. Implement PDF upload.
5. Extract PDF text.
6. Parse with OmniRoute into JSON.
7. Preview resume.
8. Export PDF.

## Future Features
- ATS scoring
- Job matching
- Resume improvements
- Cover letter generation
- LinkedIn optimization

This document is the authoritative guide for all AI-generated code.
