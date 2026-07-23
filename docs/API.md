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
| POST | /auth/login | No | Login, returns token pair |
| POST | /auth/refresh | No | Refresh access token using refresh token |
| POST | /auth/logout | Yes | Invalidate a refresh token |
| POST | /auth/logout-all | Yes | Invalidate all refresh tokens for user |
| GET | /auth/me | Yes | Get current user profile |
| PUT | /auth/me/password | Yes | Change password |

## Document Upload & Extraction

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /upload | No | Upload PDF, DOCX, or TXT file (10MB max) |
| POST | /extract | No | Extract text from an uploaded file by filename |
| POST | /parse | No | Parse extracted text into structured Resume model |

## Resume CRUD

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /resume/{id} | No | Get stored resume by ID |
| PUT | /resume/{id} | No | Update stored resume |

## PDF Generation

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /resume/{id}/pdf?template= | No | Generate resume PDF (template: executive, ats, technical, modern, minimal) |
| GET | /resume/{id}/pdf/download | No | Download generated resume PDF |
| GET | /templates | No | List available PDF template names |

## Version History

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /resume/{id}/versions | No | Create a version snapshot |
| GET | /resume/{id}/versions | No | List all versions |
| GET | /resume/{id}/versions/{vid} | No | Get a specific version |
| POST | /resume/{id}/versions/{vid}/restore | No | Restore resume from a version |

## ATS Job Matching

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /job-match | No | Analyze resume-job match (returns score, skill gaps, recommendations) |
| GET | /job-match/{id} | No | Get stored match result |

## Resume Writer (AI Suggestions)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /resume/{id}/preview-suggestion | No | Preview an AI suggestion without applying |
| POST | /resume/{id}/apply-suggestion | No | Apply an AI suggestion and create version |
| GET | /resume/{id}/writer/quick-actions | No | List quick-action prompt templates |
| POST | /resume/{id}/writer/suggest | No | Generate AI writing suggestions |
| GET | /resume/{id}/writer/suggestions | No | List pending suggestions |
| POST | /resume/{id}/writer/suggestions/{sid}/accept | No | Accept a writer suggestion |
| POST | /resume/{id}/writer/suggestions/{sid}/reject | No | Reject a writer suggestion |
| POST | /resume/{id}/writer/suggestions/{sid}/regenerate | No | Regenerate a single suggestion |

## Cover Letters

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /resume/{id}/cover-letter | No | Generate a cover letter from job description |
| GET | /resume/{id}/cover-letters | No | List all cover letters for a resume |
| GET | /resume/{id}/cover-letter/{lid} | No | Get a specific cover letter |
| PUT | /resume/{id}/cover-letter/{lid} | No | Update cover letter content |
| DELETE | /resume/{id}/cover-letter/{lid} | No | Delete a cover letter |
| GET | /resume/{id}/cover-letter/{lid}/pdf | No | Export cover letter as PDF |
| POST | /resume/{id}/cover-letter/{lid}/regenerate | No | Regenerate a cover letter |

## Job Applications

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /dashboard | No | Application dashboard summary (counts by status) |
| GET | /applications | No | List all applications (?status= filter) |
| POST | /applications | No | Create a new application |
| GET | /applications/{id} | No | Get application with linked resources |
| PUT | /applications/{id} | No | Update application fields |
| DELETE | /applications/{id} | No | Delete an application |
| PATCH | /applications/{id}/status | No | Change application status (auto-adds timeline event) |
| POST | /applications/{id}/notes | No | Add a note to an application |
| GET | /applications/{id}/timeline | No | Get timeline events |
| POST | /applications/{id}/timeline | No | Add a manual timeline event |

## Interview Intelligence

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /applications/{id}/interview/sessions | No | Create interview session |
| GET | /applications/{id}/interview/sessions | No | List interview sessions |
| GET | /applications/{id}/interview/sessions/{sid} | No | Get session details |
| PUT | /applications/{id}/interview/sessions/{sid} | No | Update session |
| DELETE | /applications/{id}/interview/sessions/{sid} | No | Delete session |
| POST | /applications/{id}/interview/sessions/{sid}/complete | No | Mark session completed |
| POST | /applications/{id}/interview/sessions/{sid}/generate-questions | No | AI-generate interview questions |
| GET | /applications/{id}/interview/sessions/{sid}/questions | No | List questions in a session |
| POST | /applications/{id}/interview/questions/{qid}/answer | No | Submit answer with optional STAR coaching |
| GET | /applications/{id}/interview/questions/{qid}/answer | No | Get answer with feedback |
| POST | /applications/{id}/interview/assess-readiness | No | AI-powered readiness assessment |
| GET | /applications/{id}/interview/readiness | No | List readiness assessments |
| POST | /applications/{id}/interview/sessions/{sid}/summary | No | Generate session summary |
| GET | /applications/{id}/interview/sessions/{sid}/summary | No | Get session summary |

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

Common error codes: `VALIDATION_ERROR`, `AUTHENTICATION_ERROR`, `NOT_FOUND`, `AI_ERROR`, `PDF_GENERATION_ERROR`, `RATE_LIMIT`.
