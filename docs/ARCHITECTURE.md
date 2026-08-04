# Architecture

## Overview

Resume Studio AI follows a layered architecture:

```
Frontend (React + MUI)
    │
    ▼ HTTP (REST JSON)
Backend (FastAPI + Python)
    ├── API Layer (routers)
    ├── Service Layer (business logic)
    ├── AI Core (shared AI infrastructure)
    ├── Storage Layer (JSON files → future PostgreSQL)
    └── Model Layer (Pydantic schemas)
    │
    ▼
OmniRoute Gateway (AI inference)
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| JSON storage (current) | Simplicity for MVP; repository pattern ready for PostgreSQL |
| Repository pattern | Swap storage backend without changing business logic |
| Externalized prompts | Modify AI behavior without code changes |
| `ai_core` package | Shared retry/parse/error logic eliminates duplication |
| Template Engine | Add new PDF themes without touching generation code |
| OwnedResource model | User isolation prepared from day one |

## Directory Structure

```
backend/
├── app/
│   ├── api/v1/          # Route handlers
│   ├── core/            # Config, logging, exceptions, middleware
│   ├── models/          # Pydantic schemas
│   └── services/        # Business logic + AI + storage
├── storage/             # JSON data files
├── tests/               # pytest suite
└── prompts/             # AI prompt templates
frontend/
├── src/
│   ├── components/      # React components
│   ├── pages/           # Route pages
│   ├── services/        # API client layer
│   ├── types/           # TypeScript interfaces
│   └── contexts/        # React contexts (auth, theme)
docs/                    # Project documentation
```

## Render Tree (Layout Engine, Phase 0)

The Render Tree is the intermediate, format-agnostic rendering document
(ADR-3.0-01). It decouples resume *structure* from any concrete output format
(HTML, PDF, DOCX, PPTX, PNG, JSON) so preview, export, and future renderers all
consume the same artifact.

- `backend/app/rendering/tree/models.py` — `NodeKind`, `RenderNode`, leaf unit
  payloads (`TextData`, `LinkData`, `TimeData`, …), `PageSize`/`PageMargins`.
- `backend/app/rendering/tree/validator.py` — `TreeValidator` (cross-node
  invariants: unique ids, region integrity, section/text provenance, span
  budget, root type) plus deterministic `extract_text()` in render order, the
  canonical ATS-order artifact.
- Structural hierarchy: `document → page → region → section → block` (block may
  be a container: `grid`/`row`/`list`/`timeline`).
- Structural invariants (child-kind rules, leaf data requirements, page
  geometry) are validated eagerly by Pydantic; global invariants are enforced by
  `TreeValidator` (`assert_valid`, `is_valid`, `validate`).
- Purely additive: the existing `TemplateRegistry`/`HTMLRenderer`/
  `PreviewService` contracts are untouched.
