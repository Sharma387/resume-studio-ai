# API Reference

Base URL: `http://localhost:8000/api/v1`

## Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /health | No | Health check |

## Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /auth/register | No | Register new user |
| POST | /auth/login | No | Login |
| POST | /auth/refresh | Refresh | Refresh access token |
| POST | /auth/logout | Yes | Invalidate refresh token |
| POST | /auth/logout-all | Yes | Invalidate all sessions |
| GET | /auth/me | Yes | Current user profile |
| PUT | /auth/me/password | Yes | Change password |

## Resume

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /upload | No | Upload PDF/DOCX/TXT |
| POST | /extract | No | Extract text from uploaded file |
| POST | /parse | No | Parse text into structured Resume |
| GET | /resume/{id} | No | Get stored resume |
| PUT | /resume/{id} | No | Update resume |

## AI Features

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /job-match | No | ATS match analysis |
| POST | /resume/{id}/preview-suggestion | No | Preview AI suggestion |
| POST | /resume/{id}/apply-suggestion | No | Apply AI suggestion |
| POST | /resume/{id}/writer/suggest | No | AI resume writer |
| POST | /resume/{id}/writer/suggestions/{sid}/accept | No | Accept writer suggestion |
| POST | /resume/{id}/writer/suggestions/{sid}/reject | No | Reject writer suggestion |
| POST | /resume/{id}/cover-letter | No | Generate cover letter |
| POST | /resume/{id}/cover-letter/{lid}/pdf | No | Export cover letter PDF |

## Applications & Interviews

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /dashboard | No | Application dashboard summary |
| GET | /applications | No | List applications |
| POST | /applications | No | Create application |
| PATCH | /applications/{id}/status | No | Change status |
| POST | /applications/{id}/interview/sessions | No | Create interview session |
| POST | /applications/{id}/interview/sessions/{sid}/generate-questions | No | AI generate questions |
| POST | /applications/{id}/interview/sessions/{sid}/complete | No | Complete session |

## Templates & PDF

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /templates | No | List available PDF templates |
| POST | /resume/{id}/pdf?template= | No | Generate resume PDF |
| GET | /resume/{id}/pdf/download | No | Download resume PDF |

## Error Response Format

All errors return:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "request_id": "abc123"
  }
}
```
