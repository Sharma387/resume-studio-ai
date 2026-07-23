# Testing Guide

## Test Stack

| Layer | Tool | Location |
|---|---|---|
| Backend unit | pytest + pytest-asyncio | `backend/tests/` |
| Backend integration | httpx + ASGITransport | `backend/tests/` |
| Frontend lint | oxlint | `frontend/` |
| Frontend type check | TypeScript (tsc) | `frontend/` |
| Frontend build | Vite | `frontend/` |

## Running Tests

```bash
# All backend tests
make test
# or
cd backend && source .venv/bin/activate && python -m pytest

# With verbose output
python -m pytest -v

# Single test file
python -m pytest tests/test_parser_service.py

# Single test
python -m pytest tests/test_parser_service.py::test_parse_success

# With coverage
python -m pytest --cov=app

# Frontend checks
make lint    # oxlint
make build   # TypeScript + Vite build
```

## Test Architecture

### Test Files

```
backend/tests/
├── test_health.py              # Health endpoint
├── test_upload.py              # File upload + validation
├── test_extract.py             # PDF/DOCX/TXT extraction
├── test_extractors.py          # Individual extractor unit tests
├── test_detector.py            # Document type detection
├── test_models.py              # Pydantic schema validation
├── test_match_models.py        # Match model validation
├── test_parse.py               # Parse API integration
├── test_parser_service.py      # Parser service unit tests
├── test_prompt_service.py      # Prompt loading + injection
├── test_omniroute_service.py   # OmniRoute HTTP client
├── test_pdf.py                 # PDF generation API
├── test_templates.py           # Template registry + rendering
├── test_resume_crud.py         # Resume CRUD API
├── test_suggestions.py         # Suggestion API
├── test_job_match.py           # Job match API
├── test_cover_letter.py        # Cover letter + PDF API
├── test_applications.py        # Application CRUD + dashboard
├── test_interviews.py          # Interview sessions + AI
├── test_writer.py              # Writer service tests
├── test_auth.py                # Auth endpoints + JWT
└── test_workspace.py           # Workspace/sync tests
```

### Test Patterns

**Unit tests** test a single service or model in isolation:

```python
def test_valid_resume():
    r = Resume(full_name="John Doe", email="john@example.com")
    assert r.email == "john@example.com"
```

**Integration tests** test full API endpoints through httpx:

```python
@pytest.mark.asyncio
async def test_upload_pdf(client):
    async with client as ac:
        resp = await ac.post("/api/v1/upload", files={...})
    assert resp.status_code == 200
```

**Mocked AI tests** replace `call_with_retry()` to avoid depending on OmniRoute:

```python
@pytest.fixture(autouse=True)
def mock_ai(monkeypatch):
    async def fake_call_with_retry(*a, **kw):
        return parse_response('{"full_name": "John"}')
    monkeypatch.setattr("app.services.parser_service.call_with_retry", fake_call_with_retry)
```

## Current Coverage

- **251** backend tests
- All API endpoints tested
- Model validation tested for all schemas
- AI services tested with mocked OmniRoute
- PDF generation tested for all 5 templates
- Auth flow tested (register → login → refresh → logout)

## Adding Tests

1. Create test file in `backend/tests/` following the naming convention `test_<module>.py`
2. Use `@pytest.mark.asyncio` for async tests
3. Use `ASGITransport(app=app)` for API tests (never reuse a closed client)
4. Mock AI via `monkeypatch.setattr("app.services.<module>.call_with_retry", ...)`
5. Run with `python -m pytest -v tests/test_<your_file>.py`

## Regression Process

Before merging any change:

1. Run full backend test suite: `make test`
2. Run frontend lint: `make lint`
3. Run frontend build: `make build`
4. Verify no new warnings or errors

## Release Validation

Before tagging a release:

1. All 251+ tests pass
2. Frontend builds with zero errors
3. Zero lint warnings
4. Manual smoke test: upload → parse → review → generate PDF → download
