# Resume Studio AI (RSAI) — Project Context

**Version:** 1.0.0  
**Last Updated:** July 2026  
**Status:** Production Ready  

---

## 1. Project Vision

### Purpose
Resume Studio AI is an AI-powered career acceleration platform that helps professionals create, optimize, and manage job applications. It transforms how users interact with their resumes by providing AI-driven parsing, ATS optimization, cover letter generation, interview preparation, and application tracking in a single workspace.

### Primary Users
- **Job seekers** actively applying for positions
- **Career changers** updating resumes for new industries
- **Professionals** preparing for interviews

### Goals
- Eliminate ATS rejection through intelligent resume optimization
- Reduce job application preparation time by 80%
- Provide actionable, AI-driven feedback for every stage of the job search
- Maintain user data privacy with strong authentication and authorization

### Current Development Stage
The platform is at v1.0.0 with 22 completed RSAI tasks spanning foundation, AI integration, document processing, job application tracking, interview preparation, authentication, and production hardening. The architecture is stable, with 251 passing backend tests and a clean frontend build.

---

## 2. Product Overview

### What the Application Does
Resume Studio AI allows users to upload a resume (PDF, DOCX, or TXT), extract its text, and parse it into a structured model using AI. Users can then edit every section, generate ATS-optimized PDFs, match their resume against job descriptions, generate cover letters, track job applications, and prepare for interviews — all within a single application.

### Supported Workflow
1. **Upload** a resume file (PDF/DOCX/TXT)
2. **Extract** text from the file
3. **Parse** into structured Resume model via AI
4. **Review and edit** the 7 resume sections
5. **Generate PDF** with one of 5 professional templates
6. **Match** against job descriptions for ATS optimization
7. **Generate** cover letters with tone selection
8. **Track** applications with status and timeline
9. **Prepare** for interviews with AI-generated questions and STAR coaching

### Current Feature Set

| Category | Features |
|---|---|
| **Document Processing** | PDF/DOCX/TXT upload, text extraction, format detection |
| **AI Parsing** | OmniRoute-powered resume parsing, structured data extraction |
| **Resume Editing** | 7-section editor (Personal Info, Summary, Skills, Experience, Education, Projects, Certifications) |
| **Version History** | Save snapshots, restore previous versions |
| **PDF Export** | 5 templates (Executive, ATS, Technical, Modern, Minimal), cover letter PDF |
| **ATS Matching** | Job description analysis, skill gap detection, AI recommendations |
| **AI Writer** | Section-level improvement suggestions, accept/reject/regenerate |
| **Cover Letters** | AI generation with tone selection, edit, PDF export |
| **Applications** | Status tracking, timeline events, notes |
| **Interview Prep** | AI question generation, STAR method coaching, readiness assessment |
| **Authentication** | JWT login/register, refresh tokens, session persistence |
| **Authorization** | User ownership on all resources, admin roles |

---

## 3. Architecture

### Backend
```
┌─────────────────────────────────────────────────┐
│                   FastAPI                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Routing  │→ │ Services │→ │ Storage      │  │
│  │ (13      │  │ (21      │  │ (JSON files) │  │
│  │  modules)│  │  modules)│  │              │  │
│  └──────────┘  └────┬─────┘  └──────────────┘  │
│                     │                          │
│              ┌──────┴──────┐                  │
│              │  AI Core    │                  │
│              │  (shared)   │                  │
│              └──────┬──────┘                  │
│                     │                          │
│              ┌──────┴──────┐                  │
│              │  OmniRoute  │                  │
│              │  Gateway    │                  │
│              └─────────────┘                  │
└─────────────────────────────────────────────────┘
```

### Frontend
```
React 19 + MUI v9 + TypeScript
├── Pages: Home (Upload), Review, Login, Register
├── Components: 28 total (review editors, UI library)
├── Services: authFetch wrapper, typed API clients
├── Contexts: AuthContext, ThemeContext
└── Routing: react-router-dom v7, ProtectedRoute
```

### AI Layer
```
Service → PromptService → call_with_retry() → OmniRouteService → HTTP
                                                     │
                                                     ▼
                                              OmniRoute API
                                                     │
Service ← parse_response() ← extract_json() ← raw response
```

### Storage
- JSON files on local disk under `storage/`
- Each entity type in its own subdirectory
- Repository pattern prepared for PostgreSQL migration
- No database currently

### Authentication
- JWT access tokens (15 min) + refresh tokens (7 days)
- bcrypt password hashing
- SHA-256 hashed refresh tokens on disk
- Token rotation on refresh
- Frontend: localStorage + authFetch wrapper with auto-refresh

### Authorization
- Every entity has a required `user_id` field
- All storage operations validate ownership
- Debug mode creates a fixed-ID dev user (`id="test"`)
- Admin role bypasses ownership checks

### Document Pipeline
```
Upload → Extension/MIME validation → UUID filename → uploads/
Extract → DocumentDetector → Extractor (PDF/DOCX/TXT) → Normalizer → Text
Parse  → PromptService → OmniRoute → JSON → Pydantic validation → Resume
```

---

## 4. Technology Stack

### Backend
| Component | Technology |
|---|---|
| Framework | FastAPI (Python 3.12+) |
| Validation | Pydantic v2 |
| Auth | python-jose (JWT), bcrypt |
| PDF | ReportLab |
| Doc Extraction | PyMuPDF (fitz), python-docx |
| AI Gateway | OmniRoute (OpenAI-compatible) |
| HTTP Client | httpx |
| Testing | pytest, pytest-asyncio, httpx |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 19 |
| UI | Material UI v9, Emotion |
| Language | TypeScript 6 (strict) |
| Build | Vite 8 |
| Routing | react-router-dom v7 |
| Linting | oxlint |

---

## 5. Folder Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, middleware, router registration
│   ├── api/
│   │   └── v1/                    # 13 route modules (61 endpoints)
│   │       ├── auth.py            # Login, register, refresh, logout
│   │       ├── applications.py    # Application CRUD + timeline
│   │       ├── cover_letter.py    # Cover letter CRUD + PDF
│   │       ├── extract.py         # Text extraction from files
│   │       ├── health.py          # Health check
│   │       ├── interviews.py      # Interview sessions + AI
│   │       ├── job_match.py       # ATS matching
│   │       ├── parse.py           # Resume parsing
│   │       ├── pdf.py             # PDF generation + templates
│   │       ├── resume_crud.py     # Resume read/update
│   │       ├── suggestions.py     # Resume versions + suggestions
│   │       ├── upload.py          # File upload
│   │       └── writer.py          # AI writer suggestions
│   ├── core/
│   │   ├── config.py              # Typed settings (env vars)
│   │   ├── error_handler.py       # Global exception handler
│   │   ├── exceptions.py          # Application exception hierarchy
│   │   ├── logging.py             # Structured JSON logging
│   │   └── middleware/
│   │       ├── request_id.py      # Request ID + timing middleware
│   │       └── security.py        # Security headers middleware
│   ├── models/                    # 9 Pydantic models
│   │   ├── resume.py
│   │   ├── cover_letter.py
│   │   ├── application.py
│   │   ├── interview.py
│   │   ├── match.py
│   │   ├── user.py
│   │   ├── version.py
│   │   ├── writer.py
│   │   └── document.py            # ExtractionResult DTO
│   └── services/
│       ├── ai_core/               # Shared AI infrastructure
│       │   ├── client.py          # call_with_retry()
│       │   ├── json_parser.py     # extract_json, extract_json_array
│       │   └── exceptions.py      # AIError, AIServiceUnavailable
│       ├── document/              # Document extraction pipeline
│       │   ├── detector.py        # File type → extractor mapping
│       │   ├── normalizer.py      # Text normalization
│       │   ├── metadata.py        # Word/char/page count
│       │   └── extractors/        # PDFExtractor, DOCXExtractor, TXTExtractor
│       ├── pdf_templates/         # PDF template engine
│       │   ├── base.py            # BaseTemplate ABC
│       │   ├── registry.py        # TemplateRegistry
│       │   ├── engine.py          # PDF rendering
│       │   └── *.py               # 5 template implementations
│       ├── repositories/          # Data access layer
│       │   ├── interfaces.py      # UserRepository, RefreshTokenRepository ABCs
│       │   ├── json_user_repo.py  # JSON user storage
│       │   └── json_token_repo.py # JSON token storage
│       ├── application_service.py
│       ├── auth_deps.py           # require_user, require_admin dependencies
│       ├── auth_service.py        # JWT creation/validation
│       ├── cover_letter_service.py
│       ├── cover_letter_pdf.py    # Cover letter PDF generation
│       ├── extract_service.py     # Document extraction orchestration
│       ├── interview_service.py
│       ├── matching_service.py
│       ├── omniroute_service.py   # AI gateway HTTP client
│       ├── parser_service.py      # Resume parsing orchestration
│       ├── pdf_service.py         # PDF generation facade
│       ├── prompt_service.py      # Prompt template loader (cached)
│       ├── storage_service.py     # JSON CRUD for all entities
│       ├── suggestion_service.py  # AI suggestion application
│       ├── upload_service.py      # File upload validation
│       ├── user_service.py        # User CRUD + password hashing
│       └── writer_service.py      # AI writer suggestion generation
├── tests/                         # 26 test files, 251 tests
├── storage/                       # JSON data files (gitignored)
└── prompts/                       # 13 AI prompt templates

frontend/
├── src/
│   ├── App.tsx                    # Routing configuration
│   ├── main.tsx                   # Entry point
│   ├── config.ts                  # API URL config (VITE_API_URL)
│   ├── index.css                  # Global styles + animations
│   ├── components/
│   │   ├── ui/                    # 6 reusable components
│   │   │   ├── ConfirmDialog.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   ├── LoadingOverlay.tsx
│   │   │   ├── SectionHeader.tsx
│   │   │   ├── SkeletonLoader.tsx
│   │   │   └── StatusBadge.tsx
│   │   ├── review/                # 10 review page section components
│   │   ├── ProtectedRoute.tsx     # Auth route guard
│   │   ├── Header.tsx
│   │   ├── UploadZone.tsx
│   │   └── FeatureCard.tsx
│   ├── pages/
│   │   ├── Home.tsx               # Landing + upload
│   │   ├── ReviewPage.tsx         # Resume editing
│   │   ├── LoginPage.tsx          # Login form
│   │   └── RegisterPage.tsx       # Registration form
│   ├── services/
│   │   ├── authFetch.ts           # Authenticated fetch wrapper
│   │   ├── authDownload.ts        # Authenticated file download
│   │   ├── authService.ts         # Login/register API calls
│   │   ├── resumeService.ts       # Resume API calls
│   │   └── uploadService.ts       # Upload/extract/parse API calls
│   ├── contexts/
│   │   ├── AuthContext.tsx         # Auth state provider
│   │   └── ThemeContext.tsx        # Dark/light theme
│   └── types/                     # TypeScript interfaces
├── docs/                          # 9 documentation files
└── prompts/                       # 13 AI prompt templates
```

---

## 6. RSAI Release History

| RSAI | Feature | Status |
|---|---|---|
| 001 | Project Foundation — FastAPI scaffold, React + Vite setup | ✅ Complete |
| 002 | SaaS Landing Page — glassmorphism UI, drag-drop upload | ✅ Complete |
| 003 | PDF Upload — MIME validation, 10MB limit, progress bar | ✅ Complete |
| 004 | PDF Text Extraction — PyMuPDF, page-by-page, normalization | ✅ Complete |
| 005 | Resume Schema — Pydantic models, validation, TS interfaces | ✅ Complete |
| 006 | AI Parsing Pipeline — OmniRoute, PromptService, retry logic | ✅ Complete |
| 007 | Resume Review Page — 7-section editor, version history | ✅ Complete |
| 008 | Professional PDF — ReportLab, 5 templates, meaningful filenames | ✅ Complete |
| 011 | ATS Job Matching — skill gap analysis, recommendations | ✅ Complete |
| 012 | Document Intelligence — PDF/DOCX/TXT extractors, detector | ✅ Complete |
| 013 | Template Engine — BaseTemplate ABC, registry, 5 themes | ✅ Complete |
| 014 | AI Resume Writer — suggestions, accept/reject/regenerate | ✅ Complete |
| 014A | AI Core Consolidation — shared retry/parse/error utilities | ✅ Complete |
| 015 | AI Cover Letter Generator — tone selection, PDF export | ✅ Complete |
| 016 | Job Application Workspace — status tracking, timeline | ✅ Complete |
| 017 | Interview Intelligence — question gen, STAR coaching | ✅ Complete |
| 018 | Authentication — JWT, bcrypt, refresh rotation, roles | ✅ Complete |
| 018A | Frontend Auth Integration — authFetch, login page, ProtectedRoute | ✅ Complete |
| 018B | Registration UI — register page, validation | ✅ Complete |
| 018A.1 | Authenticated Downloads — blob download via authFetch | ✅ Complete |
| 019 | Engineering Cleanup — structured logging, middleware, Makefile | ✅ Complete |
| 020 | UX Polish — 6 reusable components, animations, a11y | ✅ Complete |
| 020A | Release Stabilization — auth enforcement, bug fixes, a11y | ✅ Complete |

---

## 7. Current Application Flow

```
User visits /
  ├── Not logged in → /login
  │   ├── No account → /register → auto-login → /
  │   └── Login → stores tokens → /
  └── Logged in → Home page (UploadZone)
       │
       ├── Upload PDF → /api/v1/upload → filename
       │   └── Extract → /api/v1/extract → text
       │       └── Parse → /api/v1/parse → Resume model → stored
       │           └── Navigate to /review?file={id}
       │
       ├── Review → /review?file={id}
       │   ├── Edit sections → PUT /api/v1/resume/{id}
       │   ├── Generate PDF → POST /api/v1/resume/{id}/pdf
       │   ├── Download PDF → GET /api/v1/resume/{id}/pdf/download
       │   ├── ATS Match → POST /api/v1/job-match
       │   ├── AI Writer → POST /api/v1/resume/{id}/writer/suggest
       │   ├── Cover Letter → POST /api/v1/resume/{id}/cover-letter
       │   └── Version History → GET/POST /api/v1/resume/{id}/versions
       │
       ├── Applications → POST /api/v1/applications
       │   ├── Status → PATCH /api/v1/applications/{id}/status
       │   └── Timeline → GET /api/v1/applications/{id}/timeline
       │
       └── Interview → POST /api/v1/applications/{id}/interview/sessions
           ├── Questions → POST .../generate-questions
           ├── Answer → POST .../questions/{id}/answer
           └── Readiness → POST .../assess-readiness
```

---

## 8. Data Model

### User
```
User {
    id: str (required)
    email: EmailStr (required, unique)
    password_hash: str (bcrypt)
    full_name: str
    role: "user" | "admin"
    subscription: "free" | "pro" | "enterprise"
    status: "active" | "pending" | "locked" | "disabled"
    email_verified: bool
    is_active: bool
    created_at: str (ISO datetime)
    last_login: str | None
}
```

### Resume
```
Resume {
    user_id: str (required)
    full_name: str
    email: EmailStr
    phone: str | None
    location: str | None
    linkedin: HttpUrl | None
    github: HttpUrl | None
    website: HttpUrl | None
    summary: str | None
    education: list[Education]
    experience: list[Experience]
    projects: list[Project]
    skills: list[Skill]
    certifications: list[Certification]
}
```

### CoverLetter
```
CoverLetter {
    user_id: str (required)
    id: str
    resume_id: str
    company_name: str | None
    hiring_manager: str | None
    role_title: str | None
    tone: "professional" | "enthusiastic" | "formal" | "concise"
    content: str
    subject: str | None
    created_at: str
    updated_at: str
}
```

### MatchResult (ATS)
```
MatchResult {
    user_id: str (required)
    id: str
    resume_id: str
    job_title: str | None
    overall_score: float (0-100)
    skill_matches: list[SkillMatch]
    matched_skills: list[str]
    missing_skills: list[str]
    recommendations: list[Recommendation]
    summary: str | None
    created_at: str
}
```

### Application
```
Application {
    user_id: str (required)
    id: str
    company: str
    role_title: str
    location: str | None
    url: str | None
    status: "draft" | "applied" | "screening" | "interviewing" | "offered" | "rejected" | "withdrawn" | "accepted" | "archived"
    priority: "low" | "medium" | "high"
    notes: list[ApplicationNote]
    tags: list[str]
    resume_id: str | None
    cover_letter_ids: list[str]
    match_ids: list[str]
    version_ids: list[str]
    created_at: str
    updated_at: str
}
```

### InterviewSession
```
InterviewSession {
    user_id: str (required)
    id: str
    application_id: str
    title: str
    session_type: "mock" | "preparation" | "real_notes"
    question_count: int
    readiness_score: float | None (0-100)
    completed: bool
    created_at: str
    updated_at: str
}
```

---

## 9. Authentication Model

- **Registration:** `POST /auth/register` — creates user, returns JWT pair
- **Login:** `POST /auth/login` — validates credentials, returns JWT pair
- **Access token:** JWT, 15 min expiry, contains `sub` (user ID), `jti`, `role`
- **Refresh token:** JWT, 7 days expiry, stored as SHA-256 hash on disk
- **Token refresh:** `POST /auth/refresh` — validates refresh token, invalidates old, issues new pair
- **Logout:** `POST /auth/logout` — deletes refresh token hash
- **Password hashing:** bcrypt (12 rounds)
- **Frontend:** `AuthContext` stores tokens in `localStorage`, auto-restores session on mount, refreshes expired tokens
- **API calls:** `authFetch` wrapper automatically attaches `Authorization: Bearer <token>`, handles 401 with one retry+refresh

### Endpoint Protection
| Level | Behavior |
|---|---|
| Public | Health, register, login, refresh |
| Authenticated | All other 47+ endpoints |
| Admin | User management (future) |

---

## 10. User Ownership Model

Every user-owned entity has a required `user_id: str` field:

- `storage_service.py` functions accept optional `user_id` parameter
- Load operations return `None` if `user_id` doesn't match
- List operations filter by `user_id`
- Delete operations validate ownership before removing
- Service-layer functions (`application_service`, `interview_service`, etc.) pass `user_id` from route handlers

**Debug mode:** When `settings.debug=True`, unauthenticated requests get an auto-created dev user with ID `"test"`. This allows development without logging in.

---

## 11. API Overview

All endpoints under `/api/v1/`. Full documentation at `docs/API.md`.

| Module | Endpoints | Purpose |
|---|---|---|
| health | 1 | Health check |
| auth | 7 | Register, login, refresh, logout, me, password |
| upload | 1 | File upload (PDF/DOCX/TXT) |
| extract | 1 | Text extraction |
| parse | 1 | AI resume parsing |
| resume_crud | 2 | Resume read/update |
| pdf | 3 | PDF generate, download, template list |
| suggestions | 6 | Version CRUD + AI suggestion apply |
| writer | 6 | AI writing suggestions |
| cover_letter | 7 | Cover letter CRUD + PDF + regenerate |
| job_match | 2 | ATS match create/get |
| applications | 10 | Application CRUD + status + notes + timeline |
| interviews | 14 | Interview session CRUD + questions + answers + readiness |

---

## 12. AI Architecture

**Gateway:** OmniRoute (OpenAI-compatible HTTP API at configurable URL)

**Shared infrastructure** (`app/services/ai_core/`):
- `call_with_retry()` — generic retry loop (JSONDecodeError, ValidationError, OmniRouteError)
- `extract_json()` / `extract_json_array()` — strips markdown code blocks from AI responses
- `AIError`, `AIServiceUnavailable` — exception hierarchy

**Prompt management** (`PromptService`):
- Loads `.md` files from `prompts/` directory
- LRU-cached (max 32) to avoid repeated disk reads
- Each AI feature has its own system + user prompt template
- Template variables use `{variable}` syntax

**Available prompts** (13 total): parser, matcher, writer, cover letter, interview questions, answer coach, readiness, summary.

**Retry strategy:**
- Default: 1 retry (configurable via `OMNIROUTE_MAX_RETRIES`)
- Retries on: invalid JSON, Pydantic validation failure, OmniRoute error
- Fallback: `ParseError` raised when AI is unavailable and `ALLOW_MOCK_AI_DATA=false`

---

## 13. Storage Architecture

**Current:** JSON files on local disk under `storage/`. No database.

```
storage/
├── users/{id}.json
├── refresh_tokens/{hash}.json
├── resumes/{id}.json
├── versions/{resume_id}/{version_id}.json
├── matches/{match_id}.json
├── cover_letters/{resume_id}/{letter_id}.json
├── applications/{app_id}.json
├── timeline/{app_id}/{event_id}.json
├── interviews/{app_id}/sessions/{session_id}.json
├── writer_suggestions/{resume_id}/{suggestion_id}.json
├── pdfs/{resume_id}.pdf
├── cover_letter_pdfs/{letter_id}.pdf
└── (resumes dir + uploads dir)
```

**Future:** PostgreSQL migration prepared via repository interfaces in `app/services/repositories/`. JSON can be replaced by implementing the same `UserRepository` / `RefreshTokenRepository` interfaces with SQL.

**Key detail:** Storage must be deleted (`rm -rf storage/`) when upgrading to v1.0.0 because existing files lack the required `user_id` field.

---

## 14. Current Limitations

1. **JSON file storage** — No database. Suitable for single-user development. PostgreSQL migration planned.
2. **No background jobs** — AI operations block HTTP requests. A long parse/matching operation can timeout.
3. **No email delivery** — Password reset, email verification, and notifications are model-only.
4. **No billing** — Subscription tiers exist in the User model but no payment integration.
5. **No S3 file storage** — Uploaded files stored on local disk.
6. **No rate limiting** — API has no per-user rate limits.
7. **No login continuity** — After login, users always see the upload page regardless of existing data.
8. **passlib + bcrypt warning** — `passlib` emits a deprecation warning with `bcrypt>=5.0`. Authentication works correctly.

---

## 15. Known Technical Debt

| Item | Priority | Notes |
|---|---|---|
| `storage_service.py` has repetitive CRUD for 8 entity types | Medium | Should use generic base class |
| `_now()` helper duplicated in `application_service.py` and `interview_service.py` | Low | Should extract to shared utility |
| `UploadResult.to_dict()` and `ExtractResult.to_dict()` include `"success"` field | Low | Inconsistent with API response format |
| No `GET /resumes` endpoint to list user's resumes | Medium | Prevents login continuity |
| `AuthContext.tsx` and `authFetch.ts` both access localStorage directly | Low | Should share token helpers |
| `Header.tsx` Settings button is disabled | Low | No settings page exists |
| Created but unused: `OwnedResource` base model in `models/user.py` | Low | Not harmful but unused |

---

## 16. Coding Standards

### Backend
- Python 3.12+ type annotations
- FastAPI route handlers are async
- Pydantic v2 for all data models
- Services accept parameters, return typed objects
- Storage functions raise or return None (no exceptions for not-found)
- Structured logging via `get_logger(__name__)`
- Exceptions inherit from `AppError` for consistent error handling

### Frontend
- TypeScript strict mode
- React functional components with hooks
- Material UI v9 for all UI components
- API calls via `authFetch()` or `authDownload()`
- No class components
- Oxlint for linting
- Vite for build

### Git conventions
```
<type>(<scope>): <description>
Types: feat, fix, refactor, chore, docs, test, style
Scope: rsai-XXX or module name
```

---

## 17. Future Roadmap

### Short Term
- PostgreSQL migration (SQLAlchemy + Alembic)
- Background job queue (Redis + Arq)
- `GET /resumes` endpoint for login continuity
- Rate limiting and API key management
- Email delivery (SendGrid/Resend)

### Medium Term
- OAuth/SSO (Google, LinkedIn)
- Billing integration (Stripe)
- S3-Compatible file storage
- Monitoring and alerting (Sentry, OpenTelemetry)

### Long Term
- Public REST API with webhooks
- Enterprise multi-tenant support
- AI Career Coach
- LinkedIn Optimizer

---

## 18. Important Design Principles

1. **No data duplication** — Applications reference resumes and cover letters by ID. Entities are stored independently.
2. **Backward compatibility** — Existing APIs never break. New features add routes, never remove or change existing ones.
3. **Externalized prompts** — AI behavior is modified by editing `.md` files in `prompts/`, not by changing code.
4. **Shared AI core** — All AI services use `call_with_retry()` from `ai_core`. No duplicate retry/parse/error logic.
5. **Repository pattern** — Data access abstracted behind interfaces. Swap JSON for PostgreSQL without changing business logic.
6. **Service-layer ownership** — Authorization checks live in services, not route handlers.
7. **Thin routes** — Route handlers extract auth context, validate input, call services, format responses. No business logic in routes.
8. **Test-aware design** — Debug mode creates a fixed-ID test user so all tests can run without authentication.
