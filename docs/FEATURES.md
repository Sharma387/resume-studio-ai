# Feature Summary (RSAI-001 through RSAI-020)

## RSAI-001 — Project Foundation
FastAPI backend with health endpoint, logging, config, pytest. React + TypeScript + Vite frontend scaffold with Material UI dark theme. Project folder structure.

## RSAI-002 — SaaS Landing Page
Glassmorphism landing page with gradient background, drag-drop upload area, feature panel (AI Resume Parser, ATS Optimization, Professional Resume Builder). Header with navigation, dark mode toggle, GitHub button. Mobile responsive.

## RSAI-003 — PDF Upload
`POST /api/v1/upload` — accepts PDF, validates MIME type and extension, 10MB limit, stores with UUID filename. Frontend upload zone with drag-drop, progress bar, success/error states.

## RSAI-004 — PDF Text Extraction
PyMuPDF integration for page-by-page text extraction. `POST /api/v1/extract` returns page count, character count, cleaned text. Handles empty, corrupt, and multi-page documents.

## RSAI-005 — Resume Schema & Mock Parser
Canonical Pydantic models: `Resume`, `Education`, `Experience`, `Project`, `Skill`, `Certification` with validation. Matching TypeScript interfaces. Mock parser returns sample resume data. 23 tests.

## RSAI-006 — AI Parsing Pipeline
PromptService loads prompt templates from `prompts/` directory. OmniRouteService sends prompts to AI gateway with retry/timeout/logging. ParserService orchestrates prompt → AI → JSON extract → Pydantic validate → retry once → mock fallback.

## RSAI-007 — Resume Review Page
Editable `/review` page with left navigation (Personal Info, Summary, Skills, Experience, Education, Projects, Certifications). Add/edit/delete for Experience, Education, Projects, Certifications. Add/remove/categorize Skills. Save/Cancel with unsaved changes indicator.

## RSAI-008 — Professional PDF Generation
ReportLab PDF generation with professional layout. `POST /api/v1/resume/{id}/pdf` generates, `GET .../pdf/download` serves with meaningful filename (`resume_<name>.pdf`). Page numbers, proper spacing, automatic page breaks.

## RSAI-011 — ATS Job Matching
`POST /api/v1/job-match` compares resume against job description. Returns overall score (0-100), matched/missing skills, categorized recommendations with priority. ATS score gauge (color-coded), match summary, keyword analysis.

## RSAI-012 — Document Intelligence Engine
Modular document processing: `BaseExtractor` ABC → `PDFExtractor` (PyMuPDF), `DOCXExtractor` (python-docx), `TXTExtractor`. `DocumentDetector` maps extensions to extractors. `TextNormalizer` + `MetadataExtractor` utilities. Upload/extract supports PDF, DOCX, TXT.

## RSAI-013 — Resume Template Engine
`BaseTemplate` ABC with default renderers for all resume sections. 5 templates: Executive (water blue accent), ATS (minimal, compact), Technical (Courier font, purple), Modern (teal, generous spacing), Minimal (no colors, tight). Template registry with name→class mapping.

## RSAI-014 — AI Resume Writer
AI-powered writing suggestions per section: phrasing, grammar, skills, summary, achievements, completeness, full review. Preview before applying. Accept, reject, or regenerate each suggestion. Quick-action prompts (strengthen, grammar, skills, etc.). Configurable via dict.

## RSAI-014A — AI Core Consolidation
Shared `ai_core` package: `call_with_retry()`, `extract_json()`, `extract_json_array()`, `AIError` exception hierarchy. Eliminated 3 duplicated implementations across parser, matcher, and writer services.

## RSAI-015 — AI Cover Letter Generator
Generate cover letters from resume + job description. Tone selection: professional, enthusiastic, formal, concise. Edit before export. PDF export with letter formatting (sender → date → recipient → subject → body → signature). Regenerate, delete, copy to clipboard.

## RSAI-016 — Job Application Workspace
Application model with status tracking (draft → applied → screening → interviewing → offered → rejected → withdrawn → accepted → archived). Timeline events automatically created on status changes, notes, and milestones. Dashboard summary.

## RSAI-017 — Interview Intelligence
Interview session management. AI question generation from resume + job description. STAR method answer coaching with structured feedback. Readiness assessment with category scores. Session summaries. Timeline integration with applications.

## RSAI-018 — Authentication & User Management
User model with Role (USER, ADMIN), Subscription (FREE, PRO, ENTERPRISE), AccountStatus (ACTIVE, PENDING, LOCKED, DISABLED). JWT authentication with access tokens (15 min) and refresh tokens (7 days, SHA-256 hashed). Refresh token rotation. bcrypt password hashing. `require_user`/`require_admin` dependencies.

## RSAI-019 — Engineering Cleanup
Centralized config with typed Settings. Exception hierarchy (10 classes). Global error handler with consistent response format. Structured JSON logging with request/correlation IDs. Middleware: RequestID, Timing, SecurityHeaders. PromptService with LRU caching. Makefile. Documentation (ARCHITECTURE.md, API.md, AI.md, DEVELOPMENT.md, STORAGE.md).

## RSAI-020 — UX Polish
Reusable UI components: EmptyState, LoadingOverlay, SkeletonLoader (4 variants), ConfirmDialog, SectionHeader, StatusBadge. CSS animations (fadeIn, slideUp, scaleIn). Focus-visible accessibility. Responsive layout fixes. 0 lint warnings. 251 passing tests.
