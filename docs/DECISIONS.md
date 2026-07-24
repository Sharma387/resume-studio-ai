# RSAI Architectural and Product Decisions

**Purpose:** Record why every significant decision was made.  
**Audience:** Future developers and AI assistants.  
**Last Updated:** July 2026  

---

## Decision 001

**Title:** FastAPI selected as backend framework  
**Date:** RSAI-001 (July 2026)  
**Status:** Accepted  

**Context:** Needed a Python web framework for the backend API. Options included FastAPI, Flask, and Django.

**Decision:** Use FastAPI.

**Alternatives Considered:**
- **Flask:** More mature but requires separate libraries for validation, serialization, and async support. Would need Flask-RESTful, Flask-Pydantic, etc.
- **Django:** Heavy for an API-focused application. ORM and admin panel not needed for JSON storage. Overkill for MVP.
- **FastAPI:** Built-in Pydantic validation, automatic OpenAPI docs, native async support, modern Python type hints.

**Reasoning:** FastAPI's native Pydantic integration means models and validation are unified. Async support is critical for AI calls that may take 10-30 seconds. Automatic OpenAPI documentation reduces separate API docs work. The learning curve is lower than Django for an API-focused app.

**Consequences:**
- All route handlers are async
- Request/response validation is automatic via Pydantic
- OpenAPI docs available at `/docs` without additional tooling
- Dependency injection system used for auth middleware

**Future Considerations:** FastAPI is well-suited for the PostgreSQL migration planned after v1.0.

---

## Decision 002

**Title:** React + Vite selected for frontend  
**Date:** RSAI-001 (July 2026)  
**Status:** Accepted  

**Context:** Needed a modern frontend framework. Options included React (with CRA or Vite), Vue, and Svelte.

**Decision:** React with Vite and Material UI.

**Alternatives Considered:**
- **Create React App (CRA):** Deprecated and no longer maintained. Webpack-based build is slower than Vite.
- **Vue:** Lighter than React but smaller ecosystem for UI component libraries.
- **Svelte:** Fastest compile times but smallest ecosystem. Fewer job-seeking developers familiar with it.
- **Next.js:** Full framework with SSR — unnecessary for an authenticated SPA that doesn't need SEO.

**Reasoning:** React has the largest ecosystem, best TypeScript support, and Material UI provides a complete design system out of the box. Vite provides faster dev server startup (sub-second HMR) compared to webpack.

**Consequences:**
- Material UI v9 provides components, theming, and responsive design without custom CSS
- Vite enables fast iteration during development
- TypeScript strict mode catches type errors at build time
- No SSR — all pages are client-rendered SPAs

**Future Considerations:** If SEO becomes important for landing pages, a separate marketing site could use Next.js while the app remains SPA.

---

## Decision 003

**Title:** JSON file storage during development (no database)  
**Date:** RSAI-001 (July 2026)  
**Status:** Accepted  

**Context:** Needed persistent storage but wanted to avoid database setup overhead during rapid prototyping.

**Decision:** Use JSON files on disk for all data persistence.

**Alternatives Considered:**
- **PostgreSQL:** Requires installation, schema migrations, connection pooling. Adds operational complexity.
- **SQLite:** Simpler than PostgreSQL but still requires schema management and an ORM.
- **JSON files:** Zero setup, no schema migrations, data is human-readable and debuggable.

**Reasoning:** For an MVP with a solo developer, JSON files provide immediate persistence without any infrastructure. Pydantic models serialize directly to JSON. The trade-off was accepted: no query capability, no concurrent write safety, no transactions.

**Consequences:**
- Each entity type has its own directory under `storage/`
- File reads/writes use `json.loads()` / `model_dump_json()`
- No query language — list operations iterate all files and filter in memory
- No concurrent write protection — single-user development assumption
- Storage must be manually reset when schema changes

**Future Considerations:** Repository interfaces in `app/services/repositories/` prepare for PostgreSQL migration. The storage service would be replaced with SQL queries. The business services would not change.

---

## Decision 004

**Title:** OmniRoute as AI inference gateway  
**Date:** RSAI-006 (July 2026)  
**Status:** Accepted  

**Context:** Needed an AI provider for resume parsing, ATS matching, writing suggestions, cover letter generation, and interview coaching.

**Decision:** Use OmniRoute, an OpenAI-compatible API gateway that routes to multiple model providers.

**Alternatives Considered:**
- **OpenAI directly:** Requires API key management, no model fallback, higher cost for some operations.
- **Anthropic directly:** Same limitations as OpenAI.
- **Local models (Ollama):** No GPU available on development machine. Slow inference.
- **OmniRoute:** Runs locally as a gateway, routes to multiple providers, provides model fallback, free tier available.

**Reasoning:** OmniRoute provides an OpenAI-compatible API so existing tools (httpx, prompt patterns) work without modification. The gateway handles retries, fallbacks, and provider selection. Running locally means no API keys needed for development.

**Consequences:**
- All AI services use a single `OmniRouteService` HTTP client
- API format matches OpenAI chat completions (`model`, `messages`, `temperature`)
- Default model: `kiro/claude-haiku-4.5` via OmniRoute
- Configurable via environment variables (`OMNIROUTE_API_URL`, `OMNIROUTE_API_KEY`, `OMNIROUTE_MODEL`)

**Future Considerations:** The `omniroute_service.py` is a thin HTTP wrapper. Replacing it with a different provider requires changing only that file. The service layer never interacts with OmniRoute directly — it uses `call_with_retry()` from `ai_core`.

---

## Decision 005

**Title:** Externalized AI prompt templates  
**Date:** RSAI-006 (July 2026)  
**Status:** Accepted  

**Context:** AI behavior needed to be adjustable without changing code. Prompts were initially hardcoded in service files.

**Decision:** Store all AI prompts as separate `.md` files in a `prompts/` directory.

**Alternatives Considered:**
- **Hardcoded strings in Python files:** Difficult to iterate on prompts, requires redeployment for changes.
- **Database storage:** Over-engineered for text files. Prompts change rarely.
- **Separate `.md` files:** Easy to edit, version-controlled alongside code, no database needed.

**Reasoning:** Prompt engineering is iterative. Having prompts as separate files means non-developers (product, domain experts) can edit them without touching code. Markdown is human-readable and supports syntax highlighting in editors.

**Consequences:**
- `PromptService` loads `.md` files from `prompts/` directory
- LRU-cached (max 32) to avoid repeated disk reads
- Each AI feature has a system prompt + user prompt template
- Template variables use `{variable}` syntax
- 13 prompt files total covering all AI features

**Future Considerations:** Adding a new AI feature means creating two `.md` files and one `build_*_prompt()` method. No code changes to existing features.

---

## Decision 006

**Title:** Generic template engine for PDF generation  
**Date:** RSAI-013 (July 2026)  
**Status:** Accepted  

**Context:** Needed to support multiple resume PDF visual themes without duplicating PDF generation logic.

**Decision:** Create a `BaseTemplate` abstract class with a `TemplateRegistry` for name-to-class resolution.

**Alternatives Considered:**
- **Single hardcoded layout:** Simplest but one-size-fits-all. Users want different styles for different industries.
- **CSS-based HTML→PDF:** Good for pixel-perfect layouts but adds a browser dependency (WeasyPrint, wkhtmltopdf).
- **ReportLab with template pattern:** ReportLab is already used. A template class per theme with shared base logic.

**Reasoning:** The template pattern allows each theme to override only the styles and spacing it needs. The base class provides default renderers for all resume sections. Adding a theme is one class file + one registry registration.

**Consequences:**
- 5 templates: Executive (default), ATS, Technical, Modern, Minimal
- `TemplateRegistry.get(name)` returns template instance
- `GET /api/v1/templates` lists available templates
- `?template=` parameter on PDF generation endpoint
- Template only controls styling, not content structure

---

## Decision 007

**Title:** AI Writer uses suggestion-based workflow, not direct editing  
**Date:** RSAI-014 (July 2026)  
**Status:** Accepted  

**Context:** Needed AI-powered resume improvement without allowing the AI to directly modify user data.

**Decision:** AI generates suggestions that users preview, accept, reject, or regenerate.

**Alternatives Considered:**
- **Direct editing:** AI modifies resume in place. Risk of unwanted changes, user loses control.
- **Suggestion-based:** AI returns proposed changes. User decides what to apply. More work for user but safer.

**Reasoning:** Resume data is personal and critical. Users must have full control over what changes are applied. The suggestion pattern gives users visibility into what would change before committing.

**Consequences:**
- Suggestions stored in `writer_suggestions/{resume_id}/{id}.json`
- Each suggestion has `section`, `field_path`, `original_text`, `suggested_text`, `reason`, `confidence`, `status`
- Accept → updates resume + marks suggestion accepted
- Reject → marks suggestion rejected
- Regenerate → re-calls AI with same context
- `_mock_resume()` function disabled by default — requires `ALLOW_MOCK_AI_DATA=true`

---

## Decision 008

**Title:** Cover Letter has dedicated ReportLab layout, separate from resume templates  
**Date:** RSAI-015 (July 2026)  
**Status:** Accepted  

**Context:** Cover letters are prose documents (paragraphs), unlike resumes (structured sections). The resume template engine was designed for structured section rendering.

**Decision:** Create a separate `cover_letter_pdf.py` with a letter-format ReportLab layout instead of reusing the resume template engine.

**Alternatives Considered:**
- **Reuse TemplateEngine:** Would require significant changes to `BaseTemplate` to support prose flow instead of section rendering.
- **Dedicated letter generator:** Simple, focused, single-responsibility.

**Reasoning:** Cover letters have fundamentally different layout requirements: sender block, date, recipient block, subject line, body paragraphs, signature. Trying to adapt the resume template engine would create complexity in both systems.

**Consequences:**
- Cover letter PDF has its own layout in `cover_letter_pdf.py`
- Layout: sender name/contact → date → recipient → subject → body paragraphs → signature
- Not affected by template selection (always professional letter format)

---

## Decision 009

**Title:** JWT-based authentication with refresh token rotation  
**Date:** RSAI-018 (July 2026)  
**Status:** Accepted  

**Context:** Needed stateless authentication for the API. Session-based auth doesn't suit a REST API consumed by a React SPA.

**Decision:** Use short-lived JWT access tokens (15 min) with longer-lived refresh tokens (7 days) and rotation.

**Alternatives Considered:**
- **Session cookies:** Requires server-side session storage. Not stateless.
- **Long-lived JWT only:** If compromised, token is valid for a long time. No revocation mechanism.
- **JWT + refresh rotation:** Access tokens are short-lived. Refresh tokens are invalidated on each use. Compromised refresh token is detected when it fails rotation.

**Reasoning:** JWT enables stateless authentication — no session lookup on each request. Short access tokens limit damage if leaked. Refresh token rotation prevents replay attacks: if an attacker uses a stolen refresh token after the legitimate user has rotated it, the original token is already invalid.

**Consequences:**
- Access token: 15 min, stored in `localStorage`
- Refresh token: 7 days, stored in `localStorage`, SHA-256 hash on server
- Token refresh happens automatically in `authFetch` on 401 response
- Logout deletes refresh token hash (single session) or all hashes (all devices)
- Frontend `AuthContext` restores session from stored tokens on page load

---

## Decision 010

**Title:** User ownership enforced via `user_id` field on all entities  
**Date:** RSAI-018C (July 2026)  
**Status:** Accepted  

**Context:** After authentication was implemented, there was no mechanism to prevent users from accessing each other's data. All entities were shared.

**Decision:** Add a required `user_id: str` field to every user-owned entity. Validate ownership in the storage/service layer.

**Alternatives Considered:**
- **Route-level checks:** Add `check_resource_owner()` to every route handler. Would require changes to all routes.
- **Service-level checks:** Add `user_id` parameter to all storage functions. Services validate and filter by it.
- **Middleware-level checks:** Intercept requests and inject user context. Complex and error-prone.

**Reasoning:** Service-layer checks are closest to the data. They can't be bypassed by a new route that forgets to check ownership. Adding `user_id` to storage functions means every data access path enforces ownership automatically.

**Consequences:**
- All 7 entity models gained a required `user_id` field
- Storage functions accept optional `user_id` parameter
- Load operations return `None` if `user_id` doesn't match
- List operations filter by `user_id`
- Debug mode creates a fixed-ID dev user (`id="test"`)
- Storage must be deleted before upgrading (old files lack `user_id`)

---

## Decision 011

**Title:** Landing page retained as Home for v1.0 (no dashboard)  
**Date:** RSAI-021 (rolled back), RSAI-020A (July 2026)  
**Status:** Accepted  

**Context:** RSAI-021 introduced a Dashboard with sidebar navigation. It was rolled back due to regressions in layout and routing.

**Decision:** Keep the original landing page (upload-focused) as the Home page. No dashboard for v1.0.

**Alternatives Considered:**
- **Dashboard with sidebar:** Introduced layout regressions, nested scrolling, and routing issues. Not stable enough for v1.0.
- **Original landing page:** Simple, stable, functional. Users upload their first resume immediately.

**Reasoning:** The upload page is the primary action for new users. Returning users can navigate to `/review` directly. A dashboard adds visual complexity without functional benefit for the current feature set.

**Consequences:**
- Home page (`/`) shows Header + UploadZone + FeaturePanel + Footer
- No sidebar, no workspace navigation
- Users navigate to `/review?file={id}` after upload
- No "my resumes" listing — users must know their resume ID

---

## Decision 012

**Title:** Review page as full-page editor (not a dashboard widget)  
**Date:** RSAI-007 (July 2026)  
**Status:** Accepted  

**Context:** Needed an editable view of the parsed resume. Options included inline editing on the home page, a modal, or a dedicated page.

**Decision:** Dedicated `/review` page with left navigation and right content panel.

**Alternatives Considered:**
- **Inline editing on home page:** Too complex for a single page. Would need significant scrolling.
- **Modal dialog:** Limited space for 7 sections of editing.
- **Dedicated page:** Full viewport for editing. Left nav for section switching. Right panel for content.

**Reasoning:** Resume editing requires significant screen real estate. A dedicated page with section navigation provides a desktop-app-like editing experience. The left nav shows all sections, the right panel shows the selected section's form.

**Consequences:**
- 7 section editors: Personal Info, Summary, Skills, Experience, Education, Projects, Certifications
- Action bar: Save, Cancel, Generate PDF, Download PDF, Version History
- Left sidebar for section navigation (240px)
- Unsaved changes indicator
- Version history drawer (right side)

---

## Decision 013

**Title:** RSAI feature numbering skips from 008 to 011  
**Date:** Multiple (July 2026)  
**Status:** Accepted  

**Context:** During development, RSAI-009 and RSAI-010 were planned but not implemented. The numbering gap is intentional.

**Decision:** Features are numbered sequentially by completion order, not by planning order.

**Reasoning:** Not all planned features are implemented. The numbering reflects what was actually built. Skipped numbers (009, 010) represent features that were deprioritized or superseded.

**Consequences:**
- RSAI-009: (not implemented)
- RSAI-010: (not implemented)
- RSAI-011: ATS Job Matching

---

## Decision 014

**Title:** Release tags use semantic versioning but RSAI task IDs for sprint tracking  
**Date:** Throughout (July 2026)  
**Status:** Accepted  

**Context:** Needed both version numbers for releases and task IDs for sprint tracking.

**Decision:** Use semantic versioning (`v0.1`, `v0.2`, ..., `v1.0.0`) for releases. Use `RSAI-NNN` for feature task tracking. Both coexist in the repository.

**Reasoning:** Version numbers communicate the release stage to users. RSAI task IDs communicate the engineering scope internally. A single release may contain multiple RSAI tasks.

**Consequences:**
- Git tags: `v0.1`, `v0.2`, ..., `v1.0.0`
- RSAI tasks: `RSAI-001` through `RSAI-020A`
- Version in `config.py`: `1.0.0`
- Frontend `package.json` version: `1.0.0`

---

## Decision 015

**Title:** Documentation stored in `docs/` as Markdown, version-controlled  
**Date:** RSAI-019 (July 2026)  
**Status:** Accepted  

**Context:** Needed documentation for the project. Options included README-only, wiki, or version-controlled Markdown.

**Decision:** Store all documentation in `docs/` as Markdown files, version-controlled alongside code.

**Alternatives Considered:**
- **README only:** Too limited for a project of this size.
- **GitHub Wiki:** Not version-controlled with code. Easy to forget to update.
- **Separate documentation site:** Overhead of building and maintaining.
- **`docs/` Markdown:** Version-controlled, reviewable in PRs, renderable on GitHub.

**Reasoning:** Documentation that lives with code is more likely to stay accurate. Markdown is universally renderable (GitHub, VSCode, editors). No build step required.

**Consequences:**
- 9 Markdown files in `docs/` covering architecture, API, AI, deployment, development, features, security, storage, testing
- `PROJECT_CONTEXT.md` as single source of truth
- `DECISIONS.md` for architectural decision records
- `docs/README.md` not needed — root README points to docs/

---

## Decision 016

**Title:** Testing strategy: pytest for backend, build-time checks for frontend  
**Date:** RSAI-001 (July 2026)  
**Status:** Accepted  

**Context:** Needed a testing approach that balances coverage with development speed.

**Decision:** Backend uses pytest with integration tests through httpx. Frontend uses TypeScript strict mode + build-time checks.

**Alternatives Considered:**
- **Frontend unit tests (Jest/React Testing Library):** Would increase test count but slow down iteration. The UI is form-heavy with little complex state logic.
- **End-to-end tests (Playwright):** Valuable but high maintenance for a solo developer. Planned for future.

**Reasoning:** Backend contains the complex business logic (AI orchestration, parsing, validation, PDF generation). All API endpoints are integration-tested. Frontend is primarily form rendering and API calls — TypeScript catches type mismatches, and the build validates imports.

**Consequences:**
- 251 backend tests across 26 test files
- Frontend: `tsc -b` + Vite build for type and build validation
- `oxlint` for frontend linting
- No frontend unit tests currently
- AI services tested with mocked `call_with_retry()`

---

## Decision 017

**Title:** One authenticated session per browser (localStorage-based)  
**Date:** RSAI-018A (July 2026)  
**Status:** Accepted  

**Context:** Needed to persist the user's authentication session across browser refreshes.

**Decision:** Store access and refresh tokens in `localStorage`. One session per browser.

**Alternatives Considered:**
- **httpOnly cookies:** More secure against XSS but requires cookie-based CSRF protection and same-site configuration.
- **sessionStorage:** Lost on tab close. Poor UX.
- **localStorage:** Simple, persists across tabs and restarts. Accessible to JavaScript (XSS risk).

**Reasoning:** localStorage is the simplest approach for an SPA. The access token is short-lived (15 min), limiting the damage if leaked. The refresh token rotation limits replay attacks. XSS protection is handled by React's built-in escaping.

**Consequences:**
- Tokens stored in `localStorage` under `rsai_access_token` and `rsai_refresh_token`
- `AuthContext` restores session on mount
- `authFetch` handles 401 with automatic refresh
- If refresh fails, tokens are cleared and user is redirected to `/login`
- No multi-tab synchronization (each tab independently manages its session)

---

## Decision 018

**Title:** Storage service uses flat CRUD functions (not class-based)  
**Date:** RSAI-003 through RSAI-016 (July 2026)  
**Status:** Accepted  

**Context:** Needed storage operations for multiple entity types. Early code used standalone functions with hardcoded paths.

**Decision:** Keep `storage_service.py` as a module-level collection of CRUD functions rather than refactoring into classes.

**Alternatives Considered:**
- **Class-based repositories:** Would require refactoring all 50+ call sites. Introduces risk during stabilization.
- **Generic `BaseRepository<T>`:** Implemented partially in RSAI-021 but rolled back due to scope creep.

**Reasoning:** The flat function approach works and all 251 tests pass. Refactoring storage to a class-based pattern would change every file that imports from `storage_service` without adding functional value. The `BaseStorage` class exists at `storage/base.py` but is unused — it was part of RSAI-021 and rolled back.

**Consequences:**
- `storage_service.py` is 359 lines with repetitive CRUD patterns
- Each entity has its own `save_*`, `load_*`, `list_*`, `delete_*` functions
- Functions accept `user_id` parameter for ownership checks
- This is acknowledged technical debt but not blocking v1.0

---

## Decision 019

**Title:** Resume review workflow: upload → extract → parse → redirect to review  
**Date:** RSAI-007 (July 2026)  
**Status:** Accepted  

**Context:** Needed a flow that takes users from file upload to resume editing with minimal friction.

**Decision:** Chain the operations: upload → auto-extract → auto-parse → navigate to `/review?file={id}`.

**Alternatives Considered:**
- **Manual step-by-step:** User uploads, then clicks "Extract", then clicks "Parse", then clicks "Review". More control but more friction.
- **All-in-one endpoint:** Single endpoint that uploads, extracts, and parses. Hides complexity but makes error handling harder.
- **Chained with loading states:** UploadZone manages the full flow with progress indicators. Navigates automatically when ready.

**Reasoning:** The chained approach gives visual feedback at each step (upload progress, extracting spinner, parsing spinner) while not requiring user interaction between steps. The user only needs to select a file and wait.

**Consequences:**
- `UploadZone` manages 7 states: idle, dragging, uploading, extracting, parsing, success, error
- Each state has appropriate UI (progress bar, spinner, success animation)
- On success, automatically navigates to `/review?file={id}`
- No manual intervention needed between upload and review

---

## Decision 020

**Title:** Existing users see Continue Editing on the home page after login  
**Date:** RSAI-020B (July 2026)  
**Status:** Accepted  

**Context:** After login, all users were redirected to the upload page regardless of whether they had existing resumes. Returning users had to re-upload or manually navigate to `/review?file={id}`.

**Decision:** Add a `GET /resumes` endpoint that returns the current user's resumes. On the home page, check for existing resumes and show a "Continue Editing" card when one exists.

**Alternatives Considered:**
- **Dashboard with resume list:** Over-engineered for a simple continuation action. RSAI-021 (dashboard) was rolled back.
- **Automatic redirect to review:** If a user has only one resume, redirect immediately. Didn't account for users who want to upload a new resume instead.
- **Continue Editing card alongside upload:** Users can choose either action without being forced into a workflow.

**Reasoning:** The upload page is the primary action for new users. Returning users need a clear path back to their work without re-uploading. The Continue Editing card provides this without obstructing the upload flow. Both actions are visible and equally accessible.

**Consequences:**
- `GET /resumes` endpoint lists user's resumes (filtered by `user_id`, limited to 10)
- Home page fetches resumes on mount when authenticated
- Existing users see a "Continue Editing" card below the upload zone
- New users see only the upload zone (no card)
- Review page has a `← Back` button to return to Home
- Resume `id` is inferred from the filename (not a model field) and injected at the API layer

**Future Considerations:** If users accumulate multiple resumes, a "My Resumes" view may become necessary. For now, the first resume is used.
