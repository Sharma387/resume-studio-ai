# Resume Template & RenderTree Architecture

This document is the engineering reference for the canonical resume rendering
pipeline (the **Layout Engine**). It describes the template/layout schema and
registries, the RenderTree intermediate document, the layout-engine internals,
the cross-format output pipelines, the theme/CSS isolation strategy, and the
end-to-end data-flow contract.

The retired legacy stack (TemplateRegistry, Jinja HTMLRenderer, ReportLab,
`template_id` mapping shims) is removed; this RenderTree pipeline is the sole
resume rendering system.

All paths are relative to `backend/` unless prefixed with `frontend/`.

---

## 1. Template / layout definition schema and registries

A "template" is a **`LayoutDefinition`** — a fully declarative, immutable
description of structure. Layouts never render anything; they are consumed by
the tree builder and the renderers.

### 1.1 The `LayoutDefinition` model

Defined in `app/rendering/layout/layout_definition.py`.

| Component | Role |
|---|---|
| `LayoutMetadata` | Registry identity + descriptive data. `layout_id` (e.g. `"executive"`) is the registry key; `stable_id` (`layout.executive.v1`) is the permanent versioned identity. Carries semver `version`/`api_version`/`engine_version`, `ats_score`, `ats_safe`, `recommended_sections`, and `supports_*` flags. |
| `LayoutCapabilities` | What the layout can express: `sidebar`, `timeline`, `photo`, `badges`, `metrics`, `tables`, `multi_column`, `multi_page`, `qr_code`, `portfolio`, `icons`, plus `has(capability)`. |
| `regions` | `RegionDefinition` tuple (order-preserving). Each region has `identifier`, `display_name`, `region_type`, `column_span`, `ordering`, `allowed_sections`, `required`, `repeatable`. |
| `placement_rules` | `PlacementRule` tuple: per-section `preferred_region`, `fallback_region`, `allowed_regions`, `required`, `min/max_occurrences`, `ordering`, `default_variant`. |
| `grid` | `GridConfig`: `columns` (default 12), `template_areas`, `column_ratios` (rail,main) fr pair, `gap_mm`, `max_content_width_mm`. |
| `page` | `PageOptions`: `page_size` (A4/Letter) and `margins` in mm. |
| `validation` | `ValidationRules` (main-region requirement, min/max regions, placement/allow-empty rules). |
| `theme_compatibility` | Optional whitelist of supported themes (`supported_theme_ids`, `supports_any_theme`). |

`LayoutDefinition` validates eagerly on construction:

- at least one region; unique region identifiers; region spans fit the grid
  budget (full-width regions own a row, partial spans sum ≤ columns);
- capability ↔ metadata consistency (`_CAPABILITY_SYNC`), e.g. a SIDEBAR
  region forces `capabilities.sidebar`, more than one region forces
  `capabilities.multi_column`;
- placement rules reference only declared regions and known section types;
- placement rules required unless `allow_empty_placement`.

`RegionType` (`app/rendering/layout/layout_regions.py`): `header`, `main`,
`sidebar`, `footer`, `full_width`, `custom`.

### 1.2 The `LayoutRegistry`

`app/rendering/layout/layout_registry.py` — thread-safe registry keyed by both
`layout_id` and `stable_id`. It enforces an engine-version gate on
registration, rejects duplicates unless `allow_replacement`, and exposes
immutable reads: `resolve()` (raises `LayoutLookupError`),
`lookup()/get()/contains()`, `list()`, `definitions()`, `ordered()`,
`metadata()`.

The default instance is `layout_preview.default_layout_registry()`, seeded from
`REFERENCE_LAYOUTS`.

### 1.3 The six reference layouts

`app/rendering/layout/reference_layouts.py`:

| `layout_id` | Display name | Composition |
|---|---|---|
| `executive` | Executive Luxe | Full-width header (`profile`) + single main column; serif display in the CSS layer. `ats_score` 85. |
| `modern` | Editorial | Header + `main`(9-col, summary/experience/projects) + `secondary`(3-col rail). Asymmetric magazine grid. |
| `sidebar` | Modern Two-Column | `main`(8-col) + true `sidebar`(4-col tinted rail holding profile, skills, certs, languages, awards, interests). |
| `classic` | Creative Professional | Symmetric two-column: `main`(6) + `secondary`(6). |
| `timeline` | Career Timeline | Single main column; timeline rail treatment + metrics; profile/summary/experience only. |
| `minimal` | Nordic Minimal | Single main column, typography + whitespace only. `ats_score` 88. |

Each layout *declares* structure; all visual identity lives in the renderer's
per-layout CSS block keyed by the document class `layout-<id>`
(see §4.2).

### 1.4 Variants and resolution (`LayoutConfig` → `LayoutDefinition`)

`app/rendering/layout/layout_config.py` — the declarative, per-resume variant
preferences. Every value is a safe constrained enum, never raw CSS:

- `mode`: `single` | `two_column`
- `sidebar`: `left` | `right`
- `ratio`: `30/70` | `32/68` | `35/65` | `40/60`
- `gap`: `none` | `compact` | `balanced` | `wide`
- `density`: `compact` | `normal` | `spacious`
- `sections`: {section_id → `{region, order, visible}`}, `None` means inherit.

**`LayoutResolver`** (`layout_resolver.py`) is the only place that turns a
config into a concrete `LayoutDefinition`:

- `single` collapses to the structural regions (header/footer/full_width/main),
  drops the rail, clears `column_ratios`.
- `two_column` requires a main + sidebar/custom rail; re-orders by `sidebar`
  via region `ordering`; stores the ratio *exactly* as `(rail, main)` fr units
  in `column_ratios`; resolves `gap` to `gap_mm`.
- Per-section `region` overrides `PlacementRule.preferred_region` (target must
  exist and allow the section, else `LayoutResolverError`); per-section `order`
  overrides `PlacementRule.ordering`; `visible` is **not** applied (no hide
  mechanism yet).
- The base definition is never mutated — every resolution builds a new
  immutable definition and re-syncs capabilities/metadata.

**`LayoutBalancer`** (`layout_balancer.py`) is candidate *scoring only* — it
evaluates a safe preset set (single-column + 4 ratios × 2 sides), resolves each
candidate through `LayoutResolver` to prove validity, and picks the best
deterministic score (balance + main/sidebar capacity + ratio fit + simplicity).
It never mutates a definition, never renders, and never measures pages. A
supplied persisted `base_config` seeds `density`/`gap`/`sections` so user
preferences survive while the balancer still chooses
`mode`/`ratio`/`sidebar`.

**Effective-layout precedence** — single source of truth in
`layout/effective.py`, shared by preview (§3.2) and export (§3.5):

```
request-explicit layout_config
   > auto_balance=True
   > persisted layout_config
   > base layout
```

- Explicit config: authoritative; resolver errors propagate (explicit intent).
- Auto-balance (no explicit config): `ContentAnalyzer → LayoutBalancer →
  LayoutMutator`; any failure degrades silently to the base layout.
- Otherwise a persisted `base_config` is applied; an unresolvable persisted
  config (e.g. `two_column` saved for a template that was later switched to a
  rail-less one) falls back to the base layout with a warning. The frontend
  mirrors this reconciliation (`TemplateDesignerPage` caps `two_column` to
  `sidebar`/`modern`/`classic`).

The balancer also returns a `LayoutBalanceResult` (rationale + candidate
scores) that the preview API surfaces to the UI as `layout_rationale` /
`balanced_config`.

---

## 2. RenderTree and the layout-engine internals

### 2.1 The RenderTree model

`app/rendering/tree/models.py` — the intermediate, **format-agnostic** document
and the single source of truth for resume *structure*.

`NodeKind`:

- **Structural** (own children, never carry `data`):
  `document → page → region → section → block`, where `block` may itself be a
  container: `grid` / `row` / `list` / `timeline`.
- **Leaf units** (carry typed `data`, never have children): `text`,
  `paragraph`, `bullet`, `link`, `time`, `icon`, `badge`, `metric`, `image`,
  `qr_code`, `divider`, `spacer`, `page_break`.

Child-kind containment is enforced (`_ALLOWED_CHILDREN`), as is data-type/kinds
consistency via a discriminated union (`RenderUnitData`). Text-family units
derive from `TextData` and may carry styled `runs` (`InlineRun`); when `runs`
are present, renderers MUST emit the runs and `text` remains the ATS/plain-text
concatenation.

`RenderNode` fields: `id`, `kind`, `content_ref`, `region`, `span`,
`column_index`, `order`, `classes` (**structural hooks only** — never visual
CSS), `token_keys` (theme-token references), and PAGE-only geometry
(`page_size`, `margins`, `column_ratios`, `gap_mm`).

Cross-node invariants (unique ids, region references, ATS text order, span
sums, page geometry) are checked by `app/rendering/tree/validator.py`
(`TreeValidator`).

### 2.2 The `RenderContext`

`app/rendering/context/render_context.py` — the immutable, resolved inputs for
one build operation: `content_ref` (stable id + content hash only — business
data never lives in the render context), `layout` (`LayoutDefinition`), `theme`
(`ThemePalette`), `state` (`RenderState`, see below), `engine_version`.
It performs no lookups (`extra="forbid"`, frozen); registries resolve *before*
it is constructed.

`RenderState` (`context/context_state.py`): `output_format`
(html/pdf/docx/pptx/png/json), `mode` (preview/production), page numbers,
locale/timezone, `ats_mode`, `deterministic`.

### 2.3 The `ContentView` (CVM)

`app/rendering/content/models.py` — the **layout/theme/renderer-agnostic**
pure content model: `Profile`, `ExperienceEntry`, `EducationEntry`,
`SkillGroup`, `CertificationEntry`, `ProjectEntry`, `AwardEntry`,
`LanguageEntry`, `Summary`. `ContentView` carries `stable_id`, the content
fields, and a `section_order` that is *content* ordering only (layout reorders
via placement rules). `content_hash` is a deterministic SHA-256 over the
content (stable id excluded). It depends only on the shared section vocabulary
(`app/rendering/common/section_types.py`) — never on layout/theme/renderer
modules.

### 2.4 `TreeBuilder`

`app/rendering/builder/builder.py` — the L6 orchestrator. Given a CVM + a
resolved `RenderContext`, it:

1. Verifies the content reference matches the CVM (stable id + hash).
2. Derives the two-column `fr` template from `layout.grid.column_ratios` when
   the layout resolves to exactly two `MAIN`/`SIDEBAR`/`CUSTOM` column regions;
   assigns each region a `column_index` (visual left→right track order).
3. Builds one `PAGE` node (A4/Letter + margins from the layout; carries
   `column_ratios`/`gap_mm` when a two-column template exists), then a region
   node per `RegionDefinition` (sorted by `ordering`).
4. For each region, resolves which present CVM sections land there via
   `RegionDefinition` + `PlacementRule` (`_resolve_region`: preferred →
   fallback → allowed → any accepting region), sorts by rule `ordering` then
   content position (`_UNRULED_ORDER = 1_000_000` orders unrulled sections
   after rule-ordered ones), and delegates section construction to the
   `ComponentRegistry`.
5. Assembles the `DOCUMENT` node with the `layout-<id>` structural class and
   validates the whole tree with `TreeValidator`.

The builder never hardcodes layout knowledge and never contains
section-specific logic.

### 2.5 `ComponentRegistry` and the reference components

`app/rendering/components/registry.py` — thread-safe registry mapping section
types (`SectionType` values) to `SectionComponent` implementations
(`base.py`). Duplicate section types are rejected unless replacement is
allowed; the registry exposes `resolve/get/has/list/components/metadata_map`.

`app/rendering/components/reference.py` — nine lightweight-but-structural
built-in components (the `default_component_registry()` seed set): `Profile`,
`Summary`, `Experience`, `Education`, `Skills`, `Certifications`, `Projects`,
`Awards`, `Languages`. Each renders its section's CVM content into distinct
RenderTree nodes — title/company/location/dates/description, degree/institution/
gpa, grouped skills (with `InlineRun` bold category), certification/issuer/date,
etc. — so the HTML output is genuinely readable and ATS-faithful. This is the
extension seam for future section plugins.

### 2.6 The shared section vocabulary

`app/rendering/common/section_types.py` (`SECTION_REGISTRY`, `SectionType`) —
the canonical section identifiers and display names used by the TreeBuilder,
components, the HTML/DOCX renderers (for section titles), and `LayoutConfig`
validation. One source of truth across content, layout, and tree layers.

---

## 3. Cross-format output pipelines

All pipelines share the identical spine:

```
Resume → CVM → RenderContext → TreeBuilder → RenderTree → <format renderer>
```

The RenderTree is built **exactly once** per request and dispatched to the
format-specific renderer; no business/content/layout logic is duplicated per
format.

### 3.1 The three renderers

- **HTML** — `app/rendering/renderers/tree_html_renderer.py`
  (`RenderTreeHTMLRenderer`). Walks structural kinds → semantic HTML elements
  (`main.resume`, `div.resume-page`, `div.resume-region-*`, `section.resume-section`,
  `p`/`li`/`ul`/`time`/`a`, …). Determines *how it looks*, never *what goes
  where*. Emits a self-contained HTML document with an inline `<style id="rsai-theme">`.
  The renderer never inspects the CVM, LayoutDefinition, or registries.
- **PDF** — `app/rendering/renderers/tree_pdf_renderer.py`
  (`RenderTreePDFRenderer`). Reuses the HTML renderer for the same semantic
  HTML (perfect preview/PDF parity), injects `@page { size; margin }` from the
  tree's PAGE node, and converts with **WeasyPrint**.
- **DOCX** — `app/rendering/renderers/tree_docx_renderer.py`
  (`RenderTreeDOCXRenderer`). Maps tree structure to native Word objects:
  full-width regions → body paragraphs; multi-region rows → a borderless table
  with one cell per region (column widths proportional to region `span`);
  sections → headings; lists → bullets (`bullet_runs` honors `InlineRun` bold);
  links → real clickable hyperlinks; page size/margins from the PAGE node.
  Decorative kinds (image/qr/spacer) are documented no-ops; no substantive
  content is dropped.

### 3.2 React preview pipeline

`frontend/src/pages/TemplateDesignerPage.tsx` is the main preview surface.

1. `GET /api/v1/resume/layouts` and `/resume/themes` populate the pickers from
   the **registries** (frontend duplicates neither list).
2. Layout/theme live in the URL (`?resume=&layout=&theme=`), the single source
   of truth across refresh/back/forward.
3. `GET /api/v1/resume/{id}/preview?layout_id=&theme=...` (optionally
   `auto_balance=true`) resolves the **effective layout** (explicit config
   from the request is not sent for preview; persisted config is applied
   server-side; `layout_config` JSON query param is supported for explicit
   requests), then `layout_preview.generate_layout_preview` renders HTML and
   **caches it to a file** under the preview dir, keyed by MD5 over
   `content_hash + layout json + theme_id + density`.
4. `render_layout_preview_html` → `render_layout_html` → the HTML renderer.
   The response returns `preview_url`, plus `layout_rationale` & `balanced_config`
   when auto-balancing ran.
5. The SPA displays the artifact in an **iframe**; the cached file is served
   by `GET /api/v1/resume/preview/file/{filename}` (path-traversal safe).

Density (compact/normal/spacious) is forwarded through the layout-state and
implemented as additive CSS overrides (§4.4).

`TemplateGalleryPage.tsx` lists layouts from `/resume/layouts` and deep-links
into the designer.

### 3.3 Persisted customization

`GET`/`PUT /api/v1/resume/{resume_id}/layout-config` (in `api/v1/variants.py`)
persists the full normalized `LayoutConfig` under
`resume_variants.customization` (`{"layout_config": {...}}`). The designer
writes this on every control change, then regenerates the preview, so the
preview always reflects the *persisted* configuration via the server-side
precedence rule.

### 3.4 Standalone HTML / export

`frontend/src/services/exportService.ts` `downloadResumeExport` POSTs to
`/api/v1/resume/{id}/export` (`api/v1/export.py`) with `layout_id`, `theme_id`,
`format`, optional `layout_config` and `auto_balance`. `authFetch` attaches the
Bearer token and does one refresh-on-401 retry. The server returns the artifact
bytes with a `Content-Disposition` filename; the browser trigger-downloads it.

`ExportService` (`app/rendering/export_service.py`) is the canonical orches-
tration: `ExportFormat` (html/pdf/docx) → `OutputFormat`, then
`resolve_effective_layout` (same precedence as preview) → build the tree once →
dispatch to the matching renderer (density forwarded to HTML/PDF). Unknown
formats raise `ExportFormatError`. Caching is intentionally deferred; PDF/DOCX
are generated on demand.

### 3.5 Module orchestration seams

- `app/rendering/layout_html.py` — `render_layout_html/_pdf/_docx` and the
  `render_resume_layout_*` variants: `Resume → CVM → RenderContext →
  TreeBuilder → RenderTree → renderer`, with injectable registry/renderer for
  tests.
- `app/rendering/layout_preview.py` — preview cache, default layout/theme
  registries, `resolve_preview_layout`.
- `app/api/v1/rendering.py` — `GET /resume/layouts`, `/resume/themes`,
  `/resume/{id}/preview`, `/resume/preview/file/{filename}`. The retired
  `template_id` parameter is rejected explicitly. `template_id` returns 400;
  unknown layout/theme ids map to 404.

---

## 4. Theme system and CSS isolation

### 4.1 Theme model

`app/rendering/theme/`:

- `ThemeMetadata`/`ThemeVersion` — versioned identity (`theme_id`,
  `stable_id`, semver trio), `style` (`minimal…modern`), `dark_mode`,
  origin/tags.
- `ThemeTokens` (`theme_tokens.py`) — **declarative visual tokens only**:
  - `ColorTokens`: `primary`, `on_primary`, `accent`, `background`,
    `on_background`, `text`, `muted`, `border`, `success` (all `#rrggbb`).
  - `TypographyTokens`: `family`, `heading_family`, `size_scale`, `line_height`,
    weight tiers.
  - `SpacingTokens`: `unit/section/block/inline` mm + `density`.
  - `ShapeTokens`: `radius_mm`, `border_width_mm`, `shadow`.
  - `EffectTokens`: `accent_style`, `icon_style`.
- `ThemePalette` = `ThemeMetadata` + `ThemeTokens` (frozen, `extra="forbid"`).
- `ThemeRegistry` — thread-safe registry mirroring `LayoutRegistry`
  (engine-version gate, dual-key lookup, immutable reads).

The five reference themes (`reference_themes.py`): `blue`, `slate`, `forest`,
`gold`, `minimal` — data-only palettes.

### 4.2 Token → CSS-variable mapping

`RenderTreeHTMLRenderer._theme_vars` flattens the tokens into CSS custom
properties on `:root`: `--primary`, `--accent`, `--background`, `--text`,
`--muted`, `--border`, `--font-family`, `--heading-font-family`,
`--font-size-base`, `--line-height`, `--section-spacing`, `--block-spacing`,
`--inline-spacing`, `--border-width`, `--radius`, `--accent-style`, `--density`,
plus `--sidebar-bg` (a deterministic **tint** of the primary color — blended
toward white — used by tinted rails). The base stylesheet consumes only these
variables with documented fallbacks, so a theme change is a pure token swap with
zero structural impact.

### 4.3 Isolation boundaries

- **Layout ↔ theme**: themes never influence layout structure, and renderers
  decide structure via the tree (`content_ref`/`classes`/`region`), not via the
  CVM or layout objects. `RegionDefinition`/`LayoutDefinition` are layout-layer
  concerns; the HTML renderer reads only the tree + theme.
- **Per-layout CSS**: the visual identity of each layout ships as a
  `layout-<id>`-scoped CSS block (`_LAYOUT_CSS`) selected via the document
  class already present in the tree (`layout-*`). Base rules are shared; each
  layout overrides typography/color/margins/rails/timeline markers under its
  own class. Class names (`resume-*`) are *structural hooks* on tree nodes; the
  renderer maps them to style hooks.
- **Density**: `_DENSITY_SCALE` (compact 0.85 / normal 1.0 / spacious 1.2)
  scales the four spacing custom properties **at their consumer sites**
  (`_DENSITY_CONSUMERS`) with `calc(var(--x, fallback) * F)` overrides. It
  deliberately never re-declares `--x = calc(var(--x) * F)` — that is a
  self-referential custom-property cycle (guaranteed-invalid). Overrides carry
  higher specificity and are emitted later in the stylesheet. `normal`/absent
  emits nothing, so non-density output is byte-identical.
- **Print/product parity**: the PDF renderer renders the *same* HTML as the
  preview and only injects `@page` geometry; `@media print` rules clear
  screen-only chrome and control `break-inside`. Two WeasyPrint fidelity
  invariants are enforced by tests: every per-layout section-title rule keeps
  `letter-spacing` at `0`/`0.5px` (1px+ tokenizes words glyph-by-glyph in
  extracted text — the base rule's `1.2px` is overridden by all six layouts),
  and the sidebar rail section margin is `14px`. The `:has(.resume-time)` flex
  rows, `width + aspect-ratio` decorator dots, and grid-track columns are all
  matched by HTML-rendering invariants so WeasyPrint and browser output stay
  consistent.

The DOCX renderer consumes the same tokens but applies them to Word-native
styles (font names via `_font_name`, hex→`RGBColor`, heading/bullet/link
formats), with small per-layout exceptions (e.g. serif `Georgia` headings for
`executive`/`modern`, centered name for `executive`, oversized name for
`modern`).

---

## 5. Data-flow contract

### 5.1 End-to-end flow (ASCII)

```
  Frontend (React/MUI)                        Backend (FastAPI)

  TemplateGallery ──► /designer?layout=.. ──► /api/v1/resume/layouts   ──► LayoutRegistry (REFERENCE_LAYOUTS)
                        │                                             ──► /api/v1/resume/themes    ──► ThemeRegistry (REFERENCE_THEMES)
                        │
  TemplateDesignerPage ── GET /resume/{id}/layout-config ──► resume_variants.customization (persisted LayoutConfig)
      │  controls (mode/sidebar/ratio/gap/density/sections)
      │      └──► PUT /resume/{id}/layout-config                  (write)
      │                     │
      └──────── GET /resume/{id}/preview?layout_id&theme&auto_balance
              ──► resolve_effective_layout (effective.py)         (single precedence source)
                       │  ⇐ explicit config / auto-balance / persisted / base
                       ▼
              LayoutDefinition (resolved variant)
                       │
              cvm_from_resume(resume) ──► ContentView (content_hash)
                       │
              RenderContext(layout, theme, state)
                       │
              TreeBuilder + ComponentRegistry ──► RenderTree DOCUMENT
                                                       │  layout-<id> class, page geometry,
                                                       │  region tracks, sections, leaf units
                       └──► (cached to preview file, MD5-keyed)
                       └──► RenderTreeHTMLRenderer ──► HTML  ──► /resume/preview/file/{name} ──► iframe
                       └──► RenderTreePDFRenderer  ──► HTML → WeasyPrint → @page → PDF bytes

      └──────── POST /resume/{id}/export {layout_id,theme_id,format[,layout_config,auto_balance]}
              ──► ExportService ──► same effective-layout resolution
                       └──► build tree ONCE
                                ├──► HTML renderer  ──► text/html
                                ├──► PDF renderer   ──► application/pdf   ──► Response + Content-Disposition
                                └──► DOCX renderer  ──► .docx bytes              ──► browser download
```

### 5.2 Pipeline invariants

- The RenderTree is built once per request and shared across formats; renderers
  are pure tree/theme consumers with no business logic.
- Registry singletons are immutable-surface and thread-safe; layouts/themes are
  frozen Pydantic models never mutated by resolution (resolutions copy).
- Preview and export resolve the **identical** effective `LayoutDefinition`
  via `layout/effective.py` under the documented precedence rule.
- The CVM carries no layout/theme knowledge; the RenderTree carries no content
  beyond `content_ref` references and typed leaf units.
- `classes` = structural hooks; `token_keys` = theme-token references;
  visual styling is exclusively the renderer's CSS layer.
- Unknown/retired identities fail loudly: `template_id` → 400, unknown layout/
  theme → 404, unsupported/unknown export format → 400.
- Auto-balance is scoring-only and never renders; unresolvable recommendations
  and stale persisted configs degrade to the base layout (documented fallback).

### 5.3 Test surface

- Renderer unit/regression tests (HTML/PDF/DOCX), export API tests,
  `test_layout_customization_api.py`, `test_effective_layout_seam.py`, render
  tree/context validator tests, and parser tests all run against the canonical
  pipeline. The backend full suite is 1072 passed / 1 skipped; the only
  environment-dependent failures are `test_auth.py` (stale DB data) and
  `test_postgres_repositories.py` (needs Postgres).