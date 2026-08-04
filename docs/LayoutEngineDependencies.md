# Layout Engine — Dependency Map

Concise engineering map of the orchestration layer (LayoutEngine 3.0, Phases 1+).
Purpose: keep the dependency graph **acyclic** as the builder, contexts, and
renderers grow. Rule: **edges point downward only** (a module may import from
its own layer and every layer below it, never upward).

```
 L7  RENDERERS        HTMLRenderer · PDFRenderer · (DOCX/PNG/JSON future)
      ▲                     ▲             ▲
      │  (consume RenderDocument + ThemePalette tokens only)
 L6  BUILDER          TreeBuilder ────────────────► RenderDocument (+ TreeValidator gate)
      ▲                 │      │       │       │
 L5  CONTEXT           │      │  RenderContext ──► passed into component builders
      │                │      ▼       ▼       ▼
 L4  REGISTRIES        │   ComponentRegistry · LayoutRegistry · ThemeRegistry
      │                │        │
 L3  CONFIG (leaf)     │   LayoutConfig · ThemePalette     (pure data)
      │                │
 L2  CONTENT (leaf)    └──► ContentViewModel · section_types (shared vocabulary)
      │
 L1  FOUNDATION        RenderNode · NodeKind · TreeValidator · PageSize/PageMargins
```

## Module table

| Module | Owns | Depends on | Must NOT depend on |
|---|---|---|---|
| `ContentViewModel` | normalized content, section order | `Resume` (app.models), `section_types` | any rendering module |
| `LayoutConfig` | declarative layout data | `section_types`, pydantic | components, renderers |
| `LayoutRegistry` | resolve `LayoutConfig` by id | `LayoutConfig` | `ComponentRegistry`, `RenderContext`, `TreeBuilder` |
| `ThemePalette` | theme tokens | pydantic | everything |
| `ThemeRegistry` | resolve `ThemePalette` by id | `ThemePalette` | renderers (renderers take tokens, not the registry) |
| `ComponentRegistry` | section → component | `RenderNode`, `SectionComponent`, `section_types` | layouts, themes, builder, renderers |
| `RenderContext` | data bag: cvm + layout + tokens + registry + state | `ContentViewModel`, `LayoutConfig`, `ThemePalette`, `ComponentRegistry` | `TreeBuilder`, renderers |
| `TreeBuilder` | CVM + layout + registry → `RenderDocument` | `ContentViewModel`, `LayoutConfig`, `ThemeRegistry`, `ComponentRegistry`, `RenderContext`, `RenderNode`, `TreeValidator` | renderers |
| `HTMLRenderer` / future renderers | tree → format | `RenderNode`, `ThemePalette` tokens | `ContentViewModel`, registries, `TreeBuilder` |

## Forbidden edges (cycle risks)

- `Renderers → TreeBuilder / ComponentRegistry / ContentViewModel` — renderers are format consumers, never orchestrators.
- `Components → LayoutRegistry / ThemeRegistry / TreeBuilder` — components build nodes; they get layout/theme context via `RenderContext`, never by importing registries.
- `RenderContext → TreeBuilder` — the context is a data bag; it must not reach into the builder.
- `TreeBuilder → Renderers` — the builder produces a document; it never renders.
- `LayoutRegistry → ComponentRegistry` and `ThemeRegistry → ComponentRegistry` — registries are independent leaves.
- `ContentViewModel → any rendering module` — content must stay layout/theme/render agnostic.

## Shared vocabulary

`ContentViewModel`, `LayoutConfig.placement`, and `ComponentRegistry` all key on
the same **section-type strings**. A single leaf module (`section_types`) is the
source of truth for those keys — the one cross-cutting dependency that all three
may safely import. Any new section type is added there, never string-literal in
two places.

## Guardrail

Follow import-direction discipline (below-upward) in review; optionally enforce
with an import-linter contract test once the orchestration layer lands
(advisory, not yet implemented).
