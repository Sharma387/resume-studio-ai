# Layout Engine — Dependency Map

Concise engineering map of the orchestration layer (LayoutEngine 3.0, Phases 1+).
Purpose: keep the dependency graph **acyclic** as the builder, contexts, and
renderers grow. Rule: **edges point downward only** — a module may import from
its own layer and every layer below it, never upward.

## Layer hierarchy

```
 L7  RENDERERS        HTMLRenderer · PDFRenderer · (DOCX/PNG/JSON future)
                      consume RenderDocument + ThemePalette tokens only
 L6  TREEBUILDER      TreeBuilder  (CVM + configs + registries → RenderDocument,
                                    validated by TreeValidator)
 L5  RENDERCONTEXT    RenderContext  (data bag passed to component builders)
 L4  REGISTRIES       ComponentRegistry · LayoutRegistry · ThemeRegistry
 L3  CONFIG (leaf)    LayoutConfig · ThemePalette        (pure data)
 L2  CONTENT (leaf)   ContentViewModel · section vocabulary (shared leaf)
 L1  FOUNDATION       RenderNode · NodeKind · TreeValidator · PageSize/Margins
```

## Dependency diagram

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
 L2  CONTENT (leaf)    └──► ContentViewModel · section vocabulary (shared leaf)
      │
 L1  FOUNDATION        RenderNode · NodeKind · TreeValidator · PageSize/PageMargins
```

## Responsibilities

| Layer | Modules | Responsibility |
|---|---|---|
| L7 Renderers | `renderers/*` | Turn a validated `RenderDocument` + theme tokens into a concrete format. |
| L6 Input | `TreeBuilder` | Compose content + layout + registry into a `RenderDocument`; gate with `TreeValidator`. |
| L5 Context | `RenderContext` | Carry content, resolved layout, theme tokens, and registry into component builders. |
| L4 Registries | `ComponentRegistry`, `LayoutRegistry`, `ThemeRegistry` | Resolve section/layout/theme by id; registration lifecycle. |
| L3 Config | `LayoutConfig`, `ThemePalette` | Pure declarative data; never logic. |
| L2 Content | `ContentViewModel`, section vocabulary | Normalize content; the single source of section ids. |
| L1 Foundation | `tree/models.py`, `tree/validator.py` | Node model + global invariants. |

## Dependency rules

- Downward-only import policy: a module imports from its own layer and below, never upward.
- **RenderContext responsibilities**: it is a data bag (content + resolved layout + theme tokens + registry + region/order state). It must not reach into `TreeBuilder` or renderers. It is the one piece passed into component builders, so components receive layout/theme context without importing registries.
- **Registry independence**: `LayoutRegistry`, `ThemeRegistry`, and `ComponentRegistry` are mutually independent leaves — none imports another. Each resolves its own domain by id.
- **Shared section vocabulary**: `ContentViewModel`, `LayoutConfig.placement`, and `ComponentRegistry` all key on the same section-type strings. A single leaf module (`section vocabulary`) is the source of truth; any new section type is added there, never as a literal in two places.

## Forbidden dependencies (cycle risks)

- `Renderers → TreeBuilder / ComponentRegistry / ContentViewModel` — renderers are format consumers, never orchestrators.
- `Components → LayoutRegistry / ThemeRegistry / TreeBuilder` — components build nodes; they get layout/theme context via `RenderContext`.
- `RenderContext → TreeBuilder` — the context is data; it must not reach into the builder.
- `TreeBuilder → Renderers` — the builder produces a document; it never renders.
- `LayoutRegistry → ComponentRegistry` and `ThemeRegistry → ComponentRegistry` — registries are independent leaves.
- `ContentViewModel → any rendering module` — content must stay layout/theme/render agnostic.

## Future plugin considerations

- Plugins register sections/layouts/themes through the registry interfaces (L4) only — never by editing core modules.
- A plugin layout is a declarative `LayoutConfig`; a plugin section is a `SectionComponent` plus a section-vocabulary entry. Both are data + registrations, with no code reach into the builder or renderers.
- The directory lives in L3+) so a plugin can never introduce a cycle with L1/L2 foundation.

## Layout Registry (implemented)

`backend/app/rendering/layout/` — declarative, immutable layout definitions:
`LayoutMetadata` (permanent `stable_id` `layout.<name>.v1`), `LayoutCapabilities`,
`RegionDefinition`, `PlacementRule`, `ValidationRules`, and `LayoutDefinition`,
plus a thread-safe `LayoutRegistry` with a semantic-version engine gate and
lightweight reference layouts (Executive, Modern, Sidebar, Timeline, Classic,
Minimal). Pure metadata/configuration — no rendering, no TreeBuilder. Lives in
L3 (config) and imports only the L2 section vocabulary.