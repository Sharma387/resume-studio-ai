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

## Shared Section Vocabulary (Layout Engine, Phase 0)

`backend/app/rendering/common/section_types.py` — the single canonical source
of truth for every resume section identifier across the rendering architecture
(Content View Model, `LayoutConfig` placement, `ComponentRegistry`, themes,
plugins).

- `SectionType` — stable canonical section types (`summary`, `experience`,
  …). Never change.
- `SectionDefinition` — immutable (frozen) metadata: `section_type`,
  `stable_id` (permanent, e.g. `section.summary.v1`), `display_name` (mutable),
  `category`, `default_order`, `ats_priority`, `visible_by_default`,
  `supports_*` flags, `plugin_origin` (`"core"` for built-ins), `version`.
- `SectionRegistry` — thread-safe core registry: `lookup` (by section type),
  `lookup_by_id` (by stable id), `contains`, `list`, `ordered`, `validate`.
  Core definitions are immutable and cannot be replaced.
- **Plugin readiness** — marketplace plugins register dotted
  (`vendor.section`) extension definitions without modifying core; registration
  rejects duplicate stable ids, duplicate section types, empty identifiers,
  and invalid metadata. Purely additive leaf module with zero rendering
  dependencies.

## Layout Registry (Layout Engine, Phase 0)

`backend/app/rendering/layout/` — the declarative, immutable source of truth
describing every resume layout. Contains no rendering logic, no HTML/CSS, and
no TreeBuilder behaviour — pure metadata and configuration the TreeBuilder will
consume later.

- `layout_metadata.py` — immutable `LayoutMetadata` (`layout_id` registry key,
  permanent `stable_id` like `layout.executive.v1`, `version`/`api_version`/
  `engine_version`, `ats_score`/`ats_safe`, `supports_*` flags,
  `recommended_sections`, `deprecated`/`experimental`, `plugin_origin`) and
  semantic `LayoutVersion`.
- `layout_capabilities.py` — strongly typed `LayoutCapabilities`
  (`sidebar`, `timeline`, `photo`, `badges`, `metrics`, `tables`,
  `multi_column`, `multi_page`, `qr_code`, `portfolio`, `icons`).
- `layout_regions.py` — immutable `RegionDefinition` (`header`/`main`/
  `sidebar`/`footer`/`full_width`/`custom`) with `column_span`, ordering,
  `allowed_sections`, `required`, `repeatable`.
- `placement_rules.py` — declarative per-section `PlacementRule`
  (allowed/preferred/fallback regions, required, min/max occurrences,
  ordering, variant).
- `layout_validation.py` / `layout_definition.py` — `ValidationRules` and the
  `LayoutDefinition` composition (metadata + capabilities + regions +
  placement + grid + page + theme compatibility), validating region/placement/
  capability/grid/page consistency.
- `layout_registry.py` — thread-safe `LayoutRegistry` (`register`/`unregister`/
  `resolve`/`lookup`/`contains`/`ordered`/`metadata`/`definitions`/`validate`/
  `list`): deterministic ordering, duplicate layout-id and stable-id detection,
  replacement policy, semantic-version engine gate, immutable collections.
- `reference_layouts.py` — lightweight data-only reference layouts (Executive,
  Modern, Sidebar, Timeline, Classic, Minimal) validating the registry.

Stable ids are permanent (`layout.executive.v1`); display names may change.
Future marketplace layouts register through the registry without modifying core
code (extension points only — no plugin loading yet). Purely additive.

## Theme Registry (Layout Engine, Phase 0)

`backend/app/rendering/theme/` — the declarative, immutable source of truth for
visual design tokens. It sits alongside the Layout Registry and is fully
independent of it (per the dependency map). Themes control colors, typography,
spacing, shape, and effects — never layout structure.

- `theme_tokens.py` — frozen design tokens: `ColorTokens` (validated hex),
  `TypographyTokens`, `SpacingTokens` (with density), `ShapeTokens`,
  `EffectTokens`, composed into `ThemeTokens`.
- `theme_metadata.py` — immutable `ThemeMetadata` (permanent `stable_id`
  `theme.blue.v1`, semantic `ThemeVersion`, `plugin_origin`, tags, style,
  dark mode, deprecated/experimental) and versioned `ThemeVersion`.
- `theme_palette.py` — `ThemePalette` = metadata + tokens (frozen).
- `theme_registry.py` — thread-safe `ThemeRegistry`
  (`register`/`unregister`/`resolve`/`lookup`/`contains`/`ordered`/`metadata`/
  `palettes`/`validate`/`list`): duplicate theme-id and stable-id detection,
  replacement policy, semantic-version engine gate, immutable collections.
- `reference_themes.py` — five lightweight data-only themes (Blue, Slate,
  Forest, Gold, Minimal) validating the registry.

Stable ids are permanent (`theme.blue.v1`); display names may change. Future
marketplace themes register through the registry without modifying core code.
Purely additive.

## RenderContext (Layout Engine, Phase 0)

`backend/app/rendering/context/` — the immutable execution context passed into
component/layout construction. It is a **data bag** of already-resolved inputs;
it performs no lookups and holds no registries.

- `context_state.py` — strongly typed `RenderState` (`OutputFormat` enum:
  html/pdf/docx/pptx/png/json; `RenderMode` preview/production; page
  number/count; locale/timezone; accessibility/ATS/deterministic modes) — no
  renderer-specific implementation details.
- `context_validation.py` — deterministic `validate_resolved_context` (context
  compatibility only: engine-version combination, content reference).
- `render_context.py` — frozen `RenderContext` (content ref, resolved
  `LayoutDefinition`, resolved `ThemePalette`, `RenderState`) and the
  serialization-safe `ContentReference` (stable id + content hash).

**Design rules**
- **Immutable data bag** — genuinely frozen, nested models frozen; safe
  `model_copy` replace semantics.
- **Resolved dependency model** — Layout/Theme Registries resolve, then the
  resolved objects are passed in; RenderContext never calls a registry.
- **Registry independence preserved** — verified by import-graph tests
  (ThemeRegistry ⊥ LayoutRegistry ⊥ ComponentRegistry).
- **Content boundary** — the Content View Model does not exist yet; `content_ref`
  is the narrowest serialization-safe reference. Resume business data never
  lives in the context.
- **Not a service locator** — no service/container dicts, no `get_*`/`resolve`
  helpers, no generic `Any` containers.
- **Validation boundary** — declarative models validate themselves;
  RenderContext validates only the supplied *combination* (engine compatibility).
- **Relation to TreeBuilder** — TreeBuilder receives this resolved context and
  delegates section building to the ComponentRegistry; no business logic lives
  in the context.
