# PostgreSQL Setup

## Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Virtual environment activated

## 1. Start PostgreSQL

```bash
# From the project root
docker compose up -d postgres
```

This starts PostgreSQL 16 on port 5432 with:
- User: `rsai`
- Password: `rsai`
- Database: `rsai`
- Persistent volume: `pgdata`

## 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:
- `sqlalchemy[asyncio]` — async ORM
- `asyncpg` — async PostgreSQL driver
- `alembic` — migrations
- `psycopg2-binary` — sync driver for Alembic

## 3. Configure

Set these in `backend/.env`:

```env
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql://rsai:rsai@localhost:5432/rsai
```

To switch back to JSON:
```env
STORAGE_BACKEND=json
DATABASE_URL=
```

## 4. Run Migrations

```bash
cd backend
alembic upgrade head
```

To create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

## 5. Verify

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Expected PostgreSQL response:
# {"status":"healthy","version":"1.0.0","storage_backend":"postgres","database_connected":true}
```

## 6. Run Tests

```bash
cd backend

# Standard tests (JSON backend)
python -m pytest

# Infrastructure tests
python -m pytest tests/test_postgres_infrastructure.py -v
```

## Tables Created (15 total)

| Table | ORM Model | Repository |
|---|---|---|
| `users` | `UserModel` | `PostgresUserRepository` |
| `refresh_tokens` | `RefreshTokenModel` | `PostgresRefreshTokenRepository` |
| `resumes` | `ResumeModel` | `PostgresResumeRepository` |
| `applications` | `ApplicationModel` | `PostgresApplicationRepository` |
| `application_notes` | `ApplicationNoteModel` | (via ApplicationRepository) |
| `timeline_events` | `TimelineEventModel` | `PostgresTimelineEventRepository` |
| `cover_letters` | `CoverLetterModel` | `PostgresCoverLetterRepository` |
| `match_results` | `MatchResultModel` | `PostgresMatchRepository` |
| `resume_versions` | `ResumeVersionModel` | `PostgresResumeVersionRepository` |
| `writer_suggestions` | `WriterSuggestionModel` | `PostgresWriterSuggestionRepository` |
| `interview_sessions` | `InterviewSessionModel` | `PostgresInterviewSessionRepository` |
| `interview_questions` | `InterviewQuestionModel` | `PostgresInterviewQuestionRepository` |
| `interview_answers` | `InterviewAnswerModel` | `PostgresInterviewAnswerRepository` |
| `readiness_assessments` | `ReadinessAssessmentModel` | `PostgresReadinessAssessmentRepository` |
| `session_summaries` | `SessionSummaryModel` | `PostgresSessionSummaryRepository` |

## Repository Factory

All 14 repository interfaces have both JSON and PostgreSQL implementations.
The factory at `app/services/repositories/factory.py` selects the backend:

```python
STORAGE_BACKEND=json     → Json*Repository (all 14)
STORAGE_BACKEND=postgres → Postgres*Repository (all 14)
```
