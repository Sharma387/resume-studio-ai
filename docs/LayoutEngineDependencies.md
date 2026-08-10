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

## Theme Registry (implemented)

`backend/app/rendering/theme/` — declarative, immutable visual design tokens:
`ThemeTokens` (colors/typography/spacing/shape/effects), `ThemeMetadata`
(permanent `stable_id` `theme.<name>.v1`), `ThemePalette`, and a thread-safe
`ThemeRegistry` with a semantic-version engine gate and lightweight reference
themes (Blue, Slate, Forest, Gold, Minimal). Fully independent of the Layout
Registry (L3 config leaf). Themes never influence layout structure.

## RenderContext (implemented)

`backend/app/rendering/context/` — the immutable **data bag** of resolved inputs
passed into component/layout construction. Holds a `ContentReference`, the
resolved `LayoutDefinition`, the resolved `ThemePalette`, and a typed
`RenderState` (output format, mode, page, locale, ATS/a11y/deterministic flags).
Performs no lookups and imports no registries — it is the composition point
(L5) above the L3/L4 registries. Verified by import-graph tests to preserve
registry independence. Not a service locator; no business logic.

## Content View Model (implemented)

`backend/app/rendering/content/` — the layout-independent, renderer-independent
resume content (L2 content leaf): frozen `ContentView` with typed sections
(profile, summary, experience, education, skills, certifications, projects,
awards, languages), content `section_order`, and a deterministic `content_hash`,
plus a `cvm_from_resume` adapter. The same CVM flows into any `LayoutDefinition`
(Executive, Sidebar, Modern, …) unchanged — structure is the layout's concern.
CVM depends only on the shared section vocabulary; import-graph tests verify no
coupling to layout/theme/context/components/tree/service layers.

## TreeBuilder (implemented)

`backend/app/rendering/builder/` — the L6 orchestrator: `build(cvm, context)`
assembles a validated RenderTree from the CVM and `RenderContext.layout`,
resolving sections through the `ComponentRegistry` and validating with the
`TreeValidator`. Placement/composition are driven entirely by the declarative
`LayoutDefinition` (regions + placement rules) — no hardcoded layout knowledge.
Acceptance-tested: the same CVM produces materially different render structures
across Executive / Sidebar / Modern / Classic layouts with identical content.
Imports only downward (components, content, context, layout, tree) — no
renderers or preview.

## RenderTree → HTML Renderer (implemented)

`backend/app/rendering/renderers/tree_html_renderer.py` — L7 renderer consuming
the RenderTree (+ optional `ThemePalette`); emits semantic HTML with explicit
`resume-region` containers driven by region spans (never flattened, never
template-id hardcoded). `backend/app/rendering/layout_html.py` is the
orchestration seam `Resume → CVM → RenderContext → TreeBuilder → RenderTree →
HTML` (`render_layout_html` / `render_resume_layout_html`). The renderer
imports only tree/theme/common — no CVM, layouts, registries, preview, or
legacy template system. The legacy `TemplateRegistry` preview path remains
untouched; preview-API migration awaits the `template_id → layout` boundary.

## Layout Engine Preview Integration (implemented)

`backend/app/rendering/layout_preview.py` — orchestration bridging the engine
into preview behind a clean mode boundary: `?layout_id=` renders through the
new engine (CVM → RenderContext → TreeBuilder → RenderTree → HTML), while
`?template_id=` keeps the legacy TemplateRegistry path. It reuses the shared
preview cache directory (file endpoint + existing `frame-ancestors` CSP) and
adds no renderer/legacy coupling beyond that storage seam.

## Canonical layout path / legacy compatibility (template_id → layout_id)

`layout_id` is the canonical rendering identity; `template_id` is
compatibility-only. `backend/app/rendering/legacy_templates.py` is the single
mapping boundary (`TEMPLATE_TO_LAYOUT` maps all 13 legacy templates
deterministically; `resolve_legacy_template()` rejects unknown ids with
`UnknownLegacyTemplateError` — no silent fallback; `DEFAULT_LEGACY_THEME`).

```
                 CANONICAL
                     │
                     ▼
                 layout_id
                     │
                     ▼
             LayoutDefinition
                     │
                     ▼
                RenderTree
                /   |   \
             HTML  PDF  DOCX


             COMPATIBILITY
                     │
                     ▼
                template_id
                     │
                     ▼
             TEMPLATE_TO_LAYOUT
                     │
                     ▼
             legacy compatibility
```

- `layout_id` is canonical (preview + export + gallery + designer).
- `template_id` is compatibility-only, and `Resume` does not persist it.
- Preview rejects `template_id` + `layout_id` together (`400`); `template_id`
  alone stays on the byte-identical legacy path.
- `/resume/templates/{id}` exposes the mapped `layout_id`; `/resume/layouts`
  lists layouts from `REFERENCE_LAYOUTS`.
- Frontend: `/designer?layout=<id>&resume=<id>[&theme=<id>]` is canonical and
  URL is the single source of truth; `/designer?template=…` redirects to the
  mapped layout.
- Legacy rendering remains temporarily; removal is a separate future phase.