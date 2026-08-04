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

## Component Registry (Layout Engine, Phase 0)

`backend/app/rendering/components/` — the TreeBuilder's extension point for
resume sections. The TreeBuilder never contains section-specific logic; it
resolves a `SectionComponent` by section type and delegates.

- `base.py` — `SectionComponent` contract (`section_type`, `metadata`,
  `validate_input`, `build_render_nodes`), immutable `ComponentMetadata`, and
  `ComponentValidationResult`. Renderer-independent: components emit Render
  Tree nodes only (no HTML/CSS/Jinja/PDF).
- `registry.py` — thread-safe `ComponentRegistry`: `register`/`unregister`,
  `resolve`/`get`/`has`, `list`/`components`/`metadata_map`, duplicate
  detection, configurable replacement policy, deterministic registration order,
  and immutable returned collections.
- `reference.py` — lightweight placeholder components (`Summary`,
  `Experience`, `Education`, `Skills`) proving the contract end-to-end.

**Extension model** — a new resume section is a `SectionComponent` subclass
registered by section type. **Registration lifecycle** — components are
registered once at startup (duplicates rejected by default; replacement
opt-in). **Plugin readiness** — the public registry interface is the plugin
seam; future marketplace packages register components through it. Purely
additive; nothing existing is touched.

### Dependency map

The full layer hierarchy, responsibilities, downward-only import policy, and
forbidden dependencies for the orchestration layer (LayoutRegistry,
ThemeRegistry, RenderContext, ContentViewModel, TreeBuilder, renderers) live in
[`docs/LayoutEngineDependencies.md`](LayoutEngineDependencies.md).
