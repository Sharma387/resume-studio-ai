# RSAI Technical Debt Register

## Critical

| Issue | Location | Impact | Est. Effort |
|---|---|---|---|
| `InterviewSummary` GET endpoint returns 404 (stubbed) | `app/api/v1/interviews.py:104` | Feature non-functional | 1 day |
| `regenerate_suggestion()` references undefined `user_id` | `app/services/writer_service.py:105` | Runtime NameError if called | 1 hour |
| `load_interview_session()` and `_store` references in `interview_service.py` use undefined names | `app/services/interview_service.py:112,210,226` | Runtime NameError in summary generation | 1 hour |
| `load_resume()` used without import in `application_service.py` | `app/services/application_service.py:109` | Runtime NameError if `get_view()` called with `resume_id` set | 1 hour |

## High

| Issue | Location | Impact | Est. Effort |
|---|---|---|---|
| Test pollution — auth tests fail in full suite due to JSON user persistence across runs | `tests/test_auth.py` | CI flakiness | 1 day |
| `suggestion_service.py` has unused `prompt_service` and `last_error` variables | `app/services/suggestion_service.py:16,56` | Code quality | 30 min |
| Ambiguous variable name `l` in two files | `app/api/v1/cover_letter.py:25`, `app/services/pdf_templates/base.py:112` | Code quality (ruff E741) | 15 min |
| Module-level imports placed after route definitions in `admin.py` | `app/api/v1/admin.py:87,228` | Code quality (ruff E402) | 15 min |
| Exception class names without `Error` suffix | `app/services/ai_core/exceptions.py:5,13` | Naming convention (ruff N818) | 15 min |

## Medium

| Issue | Location | Impact | Est. Effort |
|---|---|---|---|
| No email infrastructure for password reset | System-wide | Admin-mediated resets only | 3 days |
| No OAuth/SSO support | System-wide | Password-only auth | 5 days |
| No multi-tenant support | System-wide | Single-tenant design | 10 days |
| No API rate limiting | System-wide | No DoS protection | 2 days |
| No pagination on `list_all()` user queries | `app/services/user_service.py` | Potential memory issue with many users | 4 hours |
| No full-text search on resumes | `app/db/models/resume.py` | Cannot search resume content | 2 days |
| Connection pool config not exposed via admin API | `app/db/database.py` | Ops limitation | 2 hours |
| Interview session metadata stored in session_id format | `app/services/storage_service.py:354` | Brittle ID encoding | 2 hours |

## Low

| Issue | Location | Impact | Est. Effort |
|---|---|---|---|
| 96 orphaned JSON test artifacts in `storage/` | `backend/storage/` | ~800KB wasted space | 30 min |
| No frontend build step linting | CI pipeline | Pre-commit hook missing | 1 hour |
| No pre-commit hooks configured | Repository root | Dev workflow gap | 1 hour |
| Ruff config in `pyproject.toml` not yet adopted by all devs | `backend/pyproject.toml` | Inconsistent formatting | 30 min |
| `_backend_name()` defined but unused | `app/services/repositories/factory.py` | Dead code | 5 min |
| Health endpoint returns `storage_backend` but no `database_connected` for JSON mode | `app/api/v1/health.py` | Inconsistent response | 15 min |

## Future Enhancements

| Feature | Est. Effort | Priority |
|---|---|---|
| Email-based password reset flow | 3 days | High |
| MFA / TOTP support | 5 days | Medium |
| Multi-tenant organizations | 10 days | Medium |
| Resume template engine v2.0 | 8 weeks | Low |
| Audit log UI with filtering/search | 2 days | Medium |
| User invitation workflow | 3 days | Medium |
| API versioning (v2) | 5 days | Low |
| Rate limiting middleware | 2 days | Medium |
| Read-only database replicas | 3 days | Low |
