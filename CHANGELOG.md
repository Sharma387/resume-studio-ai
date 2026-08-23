# Changelog

## v1.0.0-beta — Enterprise Baseline (2026-07-26)

### PostgreSQL Migration (RSAI-019 → RSAI-038)
- Complete PostgreSQL infrastructure with SQLAlchemy 2.x async + sync engines
- 15 database tables with foreign keys, indexes, check constraints, cascade rules
- Alembic migration chain (6 migrations from base to head)
- Repository Pattern with 14 PostgreSQL repository implementations
- Feature flag system (STORAGE_BACKEND) for JSON ↔ PostgreSQL switching
- Data migration utility (`scripts/migrate_data.py`) with dry-run and validation
- Production cutover with startup validation (enforces PostgreSQL in production)
- JSON repositories retained for testing and migration tools

### Administration Console (RSAI-032 → RSAI-037B)
- Full Administration Console with sidebar navigation
- Dashboard with live status cards and table counts
- AI Configuration with model selection, connection testing, model discovery
- AI parse test with sample resume snippet
- Database diagnostics with validation runner
- Storage management with PostgreSQL status
- Feature flag management (runtime toggles)
- System Health aggregated view
- Configuration Diagnostics with 5 health sections
- Development Mode status page
- Configuration abstraction service for runtime settings management

### Authentication & Security (RSAI-033C, RSAI-034, RSAI-036)
- JWT secret validation (32+ char minimum, startup enforcement in production)
- Development mode consolidation (`DevelopmentFeatures` service)
- Debug authentication hardening (invalid tokens never produce mock users)
- Mock AI data requires both ALLOW_MOCK_AI_DATA and DEBUG mode
- Production startup safety audit
- Admin bootstrap script (`scripts/create_admin.py`)
- Admin role management with promote/demote safeguards
- Admin route protection (all 19 admin endpoints use require_admin)
- Frontend admin icon visibility (role-based)
- Configuration diagnostics service (never exposes secrets)

### User Management (RSAI-038)
- User management service with list, search, disable, enable, promote, demote
- Password policy enforcement (12+ chars, upper, lower, digit, special)
- Temporary password generation (16-char secure random)
- Custom password option for admin resets
- Password strength validation
- Must-change-password login flow
- User profile page with security tab
- Audit logging for all administrative actions
- Self-demotion prevention, last-admin protection

### AI Integration (RSAI-030, RSAI-031, RSAI-032)
- OmniRoute AI service integration with retry logic
- AI connectivity health check + admin diagnostics
- Runtime model switching via Admin Console
- Model discovery from OmniRoute API
- Fixed: OmniRouteService reads model from settings at instantiation (not import time)
- Connected: model `auto/best-fast` with 120s configurable timeout

### CI/CD & Quality (RSAI-029, RSAI-038)
- GitHub Actions CI pipeline (5 jobs: quality, JSON tests, PG tests, DB validation, smoke tests)
- GitHub Actions release pipeline (pre-release checks, PG validation, auto-release)
- Ruff linting and formatting with pyproject.toml config
- pytest configuration with asyncio mode
- Docker Compose for PostgreSQL 16
- Deployment scripts (deploy, rollback, backup, smoke_test)
- Production deployment documentation
- 322 passing tests

### Navigation & UX
- ReviewGuard prevents loading review page without context
- Login redirects to Home (never /review without context)
- Profile page with change password (My Profile + Security tabs)
- Admin link on landing page (role-based visibility)
- Confirmation dialogs for all user management actions
- Error handling with friendly messages (no raw JSON parse errors)
- Empty response handling in API calls

### Operational Improvements
- Structured diagnostics on startup with issue-by-issue logging
- Application fails safely on insecure production configuration
- Health endpoint reports AI, database, and storage status
- Pool configuration (size, overflow, timeout) exposed in diagnostics
- Storage backend switching no longer supported (PostgreSQL-only production mode)
- 322 passing tests

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
