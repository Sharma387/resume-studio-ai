# Migration Plan: JSON → PostgreSQL

## Strategy

Incremental migration using the existing Repository Pattern.
Each repository is migrated independently while the rest of the system continues using JSON.

## Phases

### Phase 1 — Infrastructure (COMPLETE)

- [x] PostgreSQL Docker setup
- [x] SQLAlchemy async engine
- [x] Alembic migrations
- [x] Repository Factory with feature flag
- [x] Health endpoint with backend detection
- [x] PostgreSQL repository stubs

### Phase 2 — All Repositories (COMPLETE)

- [x] UserRepository — `PostgresUserRepository`
- [x] RefreshTokenRepository — `PostgresRefreshTokenRepository`
- [x] ResumeRepository — `PostgresResumeRepository`
- [x] ApplicationRepository — `PostgresApplicationRepository`
- [x] CoverLetterRepository — `PostgresCoverLetterRepository`
- [x] MatchRepository — `PostgresMatchRepository`
- [x] ResumeVersionRepository — `PostgresResumeVersionRepository`
- [x] WriterSuggestionRepository — `PostgresWriterSuggestionRepository`
- [x] InterviewSessionRepository — `PostgresInterviewSessionRepository`
- [x] InterviewQuestionRepository — `PostgresInterviewQuestionRepository`
- [x] InterviewAnswerRepository — `PostgresInterviewAnswerRepository`
- [x] ReadinessAssessmentRepository — `PostgresReadinessAssessmentRepository`
- [x] SessionSummaryRepository — `PostgresSessionSummaryRepository`
- [x] TimelineEventRepository — `PostgresTimelineEventRepository`

### Remaining (Future Phase)

- [ ] JSON → PostgreSQL data migration
- [ ] Switch default backend to PostgreSQL
- [ ] Remove JSON backend

## Switching Between Backends

```bash
# Use JSON (default)
STORAGE_BACKEND=json

# Use PostgreSQL
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql://rsai:rsai@localhost:5432/rsai
```

## Testing Strategy

During migration:
1. Run existing test suite with `STORAGE_BACKEND=json` — must pass
2. Run new PostgreSQL infrastructure tests — must pass
3. Per-repository: write PostgreSQL tests, run alongside JSON tests
4. Integration test with PostgreSQL — optional, requires running database
