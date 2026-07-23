# Changelog

## v0.9 — Engineering Cleanup (2026-07-22)

- Centralized configuration in `app/core/config.py` with typed settings
- Created exception hierarchy with 10 application exception classes
- Global error handler with consistent `{success, error: {code, message, request_id}}` response format
- Structured JSON logging with request/correlation IDs
- Middleware: RequestID, Timing (X-Response-Time-Ms), SecurityHeaders
- PromptService: LRU caching, validation, clear exceptions
- All services updated to use `get_logger()` from structured logging
- Makefile with dev/test/lint/build/clean targets
- Documentation: ARCHITECTURE.md, API.md, AI.md, DEVELOPMENT.md, STORAGE.md
- 251 passing tests

## v0.8 — Job Application Workspace (2026-07-21)

- Application model with status (draft → applied → interviewing → offered → ...)
- Timeline events for status changes, notes, and milestones
- ApplicationView DTO aggregates linked resources (resumes, cover letters, matches)
- Dashboard summary endpoint with counts by status/priority
- 265 passing tests

## v0.7 — AI Cover Letter Generator (2026-07-20)

- Cover letter generation from resume + job description
- Tone selection: professional, enthusiastic, formal, concise
- Edit before export; PDF export with letter formatting
- Regenerate, delete, and copy actions
- 251 passing tests

## v0.6 — AI Resume Writer (2026-07-20)

- AI-powered resume writing suggestions per section
- Accept, reject, or regenerate each suggestion
- Quick-action prompts: strengthen, grammar, skills, achievements
- `ai_core` shared package: `call_with_retry()`, JSON extraction, shared exceptions
- 251 passing tests

## v0.5 — Template Engine (2026-07-19)

- 5 professional PDF templates: Executive (default), ATS, Technical, Modern, Minimal
- TemplateRegistry with name→class mapping
- `?template=` parameter on PDF generation endpoint
- `GET /api/v1/templates` endpoint to list available templates
- 153 passing tests

## v0.4 — Document Intelligence (2026-07-19)

- Modular document processing: PDFExtractor, DOCXExtractor, TXTExtractor
- DocumentDetector with extension→extractor registry
- TextNormalizer, MetadataExtractor utilities
- Support for DOCX and TXT uploads alongside PDF
- 133 passing tests

## v0.3 — ATS Matching (2026-07-19)

- Job description matching with AI-powered analysis
- Skill gap detection (matched vs missing skills)
- AI recommendations with priority (high/medium/low)
- Preview changes before applying
- 80 passing tests

## v0.2 — AI Parsing (2026-07-19)

- OmniRoute AI integration for resume parsing
- Pydantic Resume schema with validation
- Editable review page with 7 sections
- Version history with restore
- Professional PDF generation with ReportLab
- Multiple PDF export templates
- 59 passing tests

## v0.1 — Foundation (2026-07-18)

- FastAPI backend with health endpoint
- React + TypeScript + Vite frontend scaffold
- Material UI dark theme with glassmorphism design
- SaaS landing page with drag-drop upload
- PDF upload with MIME/extension validation
- PDF text extraction via PyMuPDF
