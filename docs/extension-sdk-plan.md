# BuildSuite extension SDK — plan

Status: **phases 1, 2 and 2b implemented (see the status sections)** · Branch: `feat/extension-sdk` · Supersedes the customer-specific work on
`feat/app-extension-hooks` (see "What we keep from it").

## Goal

Let anyone customise BuildSuite Core **without forking it**: create a standard Frappe app from a
template we provide, install it on a site, and it can

- add and change **workspaces** (tiles, order, visibility),
- add **pages**, and **override or wrap** existing ones,
- extend **forms and lists** (sections, fields, save hooks),
- ship **Python** (doctypes, hooks, permissions, workflows, reports) the normal Frappe way.

The same extension points must later be drivable **from data on the site**, so an onboarding page
where a user prompts an AI, or drags and drops, can produce customisations without anyone writing
code (phase 4, designed for now, built last).

## Non-goals

- Anything specific to one customer. Core never names an app or a customer.
- A second, parallel way to do what Frappe already does (Custom Fields, Property Setters, doc_events,
  Workspaces, DocPerms). Extensions use those; the SDK only wraps the awkward parts.
- Sandboxing untrusted code in phase 1 (see Risks). Extensions are trusted, installed apps.

## Principles

1. **Standard Frappe on the backend.** An extension is an ordinary Frappe app. No Core-specific plugin
   format.
2. **Runtime frontend wiring.** Core discovers and loads extension bundles at runtime. Nothing is
   compiled into Core's bundle and Core's build never depends on other apps being present.
3. **One public SDK, two halves.** A JS SDK (reusable Vue controls and helpers) and a Python SDK
   (thin, stable wrappers over our internals). Anything not in the SDK is private and may change.
4. **Registries, not special cases.** Every extension point is a named registration, so adding a page
   or slot to Core never needs extension-specific logic.
5. **Data-shaped where possible.** Declarations (tiles, slots, overrides) are plain data so a future
   site-level editor can write the same thing.

## What already exists and is reused

| Need | Already in Core |
| --- | --- |
| Reusable controls | `components/desk/*` (DeskPage, DeskForm, DeskField, DeskInput, DeskSelect, DeskLinkPicker, DeskList, filters, pagination), `components/doctype/*` (DocTypeForm, DocTypeListView, child tables) |
| Data and state | `data/adapters`, `composables/*` (usePermissions, useDocTypeList, useDoctypeMeta, useWorkflow, useAutosave, useFormErrors, useActiveCompany) |
| Workspaces | backend registry (`api/workspace_setting.py`) and `store.workspaces` |
| Report access | `report_access.py` anchors and `is_route_permitted` |
| Seeding | create-if-missing seeds (`seed_workflows`, print formats), `utils/session.as_administrator` |
| Permissions | DocPerm matrix (`setup.py`) and the frontend-derived permission payload |
| Workflow | `api/workflow.py` and `useWorkflow` |

## Architecture

### 1. Discovery (Frappe hooks)

An extension app declares its frontend entry in its own `hooks.py`:

```python
buildsuite_frontend_extensions = [
    {"name": "acme_buildsuite", "js": "/assets/acme_buildsuite/js/extension.js", "css": "/assets/acme_buildsuite/css/extension.css", "min_sdk": "1.0"},
]
```

Core's boot reads `frappe.get_hooks("buildsuite_frontend_extensions")`. Frappe returns hooks of
**installed apps only**, so per-site gating is automatic and no `installed_apps` boot key is needed.

### 2. Loading (runtime)

After boot and before the router resolves, Core loads each entry as an ES module and calls its default
export, `register(sdk)`. Each extension is isolated in try/catch: a failing extension is logged and
skipped and never stops Core. `min_sdk` is checked against `sdk.version`; an incompatible extension is
skipped with a visible, admin-only warning.

The extension app builds its own bundle (the template ships the Vite config) with `vue`,
`vue-router`, `pinia` and `frappe-ui` as **externals**. Core supplies them (one reactivity system, one
router, one store) through an import map plus small shim modules, so extension code uses normal
`import { ref } from "vue"`.

### 3. Registries (the extension points)

Core resolves its own UI through named registries, so extensions use the same path Core does.

| Registry | Registration | Core side |
| --- | --- | --- |
| Routes | `sdk.routes.add(route)` | router adds to the named `shell` route |
| Views | `sdk.views.override(name, component)`, `sdk.views.wrap(name, wrapper)` | routes resolve views by name through the view registry |
| Slots | `sdk.slots.add(slotName, component, { when })` | pages declare `<ExtensionSlot name="quotation.form.after-items">` |
| Workspaces | `sdk.workspaces.addTile / hideTile / reorder` | existing workspace registry |
| Settings | `sdk.settings.addTile(group, tile)` | Settings hub reads the registry |
| DocType hooks | `sdk.doctype(name).defaults / onLoad / beforeSave / afterSave` | generic DocTypeForm and list call the hooks |
| Nav / theme | later | |

Slot names follow `<doctype-or-view>.<area>.<position>`. One generic `<ExtensionSlot>` component
makes every page extendable by adding one line to its template; no per-page logic.

### 4. The JS SDK (`frontend/src/sdk`)

A single entry that re-exports the **public** surface and nothing else:

- controls: the Desk* components and DocType* views listed above,
- composables: permissions, doctype meta and list, workflow, autosave, form errors, active company,
- data: the data adapter, `__()` translate, formatters, toast and confirm helpers,
- `version`, and the registration functions above.

Extensions import from the SDK (`import { DeskField } from "@buildsuite/sdk"`, mapped by the same import
map), never from `@/…`. That is the upgrade contract: the SDK surface is versioned and semver'd;
Core-internal modules are free to change.

### 5. The Python SDK (`buildsuite_core/sdk`)

Thin, documented wrappers with an explicit `__all__`, over helpers that already exist:

- `seed_if_missing(doctype, filters, values)`: the create-if-missing pattern, so an extension's
  seeds never overwrite admin edits on migrate.
- `seed_workflow(definition)`: the generalised `seed_workflows`.
- `grant_permissions(doctype, role_map)`: idempotent DocPerm helper, aware of the permission matrix.
- `register_report(name, roles, route)`: report anchor plus access, so a report appears in the right
  workspace for the right roles.
- `register_workspace_tile(workspace, tile)`: server-side registration into the workspace registry.
- `as_administrator()`, `default_company()`, `project_company(project)`.
- `get_extension_entries()`: what boot returns.
- `test` helpers: a base test class and persona login for the permission matrix.

### 6. Template and scaffold

- A template repo (and `bench buildsuite new-extension <name>`) producing: Python package with
  `hooks.py` and the hook above, a Vite config with the externals and import map, a sample
  `extension.js` using each registry once, a `tests/` folder using the Python SDK test helpers, and a
  README.
- Docs live in `docs/extensions/`: guide, SDK reference, slot catalogue, versioning policy.

### 7. Site-level data layer (phase 4)

A doctype (working name "BuildSuite Customisation") stores the same declarations as JSON (tile,
slot, view override). Boot merges them into the registries with precedence **core, then app, then
site**. An AI or drag-and-drop editor only has to write that JSON. Phases 1 to 3 keep declarations
JSON-friendly (names and props, not closures) so this needs no redesign.

## Phases

Each phase is its own PR off `develop`; nothing ships half-wired.

1. **Spike: end to end, minimal.** Hook discovery, runtime loader with isolation, `register(sdk)`,
   `routes.add`, `slots.add` + `<ExtensionSlot>` on one generic page, `workspaces.addTile`, a throwaway
   extension app outside this repo as proof. Decide the import-map approach here.
   *Done when:* the throwaway app, installed on a site, adds a page, a slot component and a workspace
   tile; uninstalling it removes all three; a deliberately broken extension does not break Core.
2. **View registry and overrides.** Move Core routes onto named views; `views.override` and `wrap`;
   DocType hooks on the generic form; first public SDK cut (`frontend/src/sdk`) and Python SDK module.
   *Done when:* an extension replaces and wraps a Core view and hooks a doctype save, with tests.
3. **Scaffold, docs, versioning.** Template, `new-extension` command, `docs/extensions/*`, semver
   check, SDK changelog, CI that fails when the public surface changes without a version bump.
4. **Site-level customisation data layer** and the editor/AI onboarding page.

## Risks and open decisions

1. **Override semantics.** `override` replaces a Core view and the extension then owns it across
   upgrades; `wrap` keeps Core's view inside. Recommend shipping both and warning in the docs that
   `wrap` is the upgrade-safe one.
2. **Trust.** Extension code shares Vue, router and store with full access. Fine for apps our team or
   partners write. If customers or an AI author them, the SDK needs a restricted store facade and
   per-extension permissions. Decide before phase 4.
3. **Import-map vs globals** for sharing Vue and friends (phase 1 spike decides).
4. **Public surface size.** Start small; adding to the SDK is cheap, removing is not.
5. **Existing per-page code.** Pages must expose slots and named views gradually. Do the high-traffic
   ones first (Quotation, Project detail, workspaces landing) and make adding the rest mechanical.

## What we keep from `feat/app-extension-hooks`

- The named `shell` route for adding pages.
- The shape of the doc hooks (`defaults`, `onLoad`, `beforeSave`, `afterSave`).

Everything else is dropped: the eager `import.meta.glob` bundling, the Quotation/Assembly-specific
slots, Rate Master repricing, Assembly Duplicate and the RichTextEditor focus change (those belong in
their own PRs if wanted).

## Verification

- Python: tests for each SDK helper (idempotent, no overwrite of admin edits), the hook reader, and
  the permission matrix with an extension installed.
- Frontend: Cypress against a fixture extension: page, slot, tile, override, a failing extension.
- A migrate on a site with the fixture extension installed leaves admin edits intact.

## Phase 1 status (spike)

Implemented on this branch:

- `buildsuite_core/sdk` (Python): `SDK_VERSION`, `get_extension_entries()` (hook discovery with
  validation: `/assets/` paths only, de-duplicated), `seed_if_missing`. Boot carries
  `buildsuite_extensions` and `buildsuite_sdk_version`.
- `frontend/src/sdk` (JS): `registry.js` (reactive slot and tile registries), `index.js` (the public
  SDK: routes, slots, workspaces, controls, composables, Vue and vue-router), `loader.js` (runtime
  load, compatibility check, per-extension isolation).
- `ExtensionSlot` and `ExtensionBoundary` components. **Every page built on `DeskPage` (120 of 165
  views) gets `page.<route name>.top` and `.bottom` slots.** Views that do not use `DeskPage` (for
  example the Home page) have none yet and need an explicit `<ExtensionSlot>`.
- Workspace tiles render in the shared Reports group (`WorkspaceReportsSection`), so a workspace
  that shows that group shows extension tiles.
- `examples/buildsuite_demo_extension`: a throwaway Frappe app that adds a page, a slot component
  and a workspace tile, plus an opt-in broken component. Cypress `extension_sdk.cy.js` covers all
  four (4 passing); `test_sdk_extensions.py` covers discovery and `seed_if_missing`.

Decided in the spike: the demo extension is a plain ES module that uses `sdk.vue` (Core's Vue),
so no import map is needed yet. The import map for independently built bundles stays an open item
for phase 2/3. Not done in phase 1: view overrides and wrap, DocType hooks, the scaffold command,
the site-level data layer.

## Phase 2 status (views and DocType hooks)

SDK version 1.1 (Python `SDK_VERSION` and JS `SDK_VERSION` move together).

- **View registry.** `sdk/views.js` walks the route table once, before the router is created, and makes
  every named lazy route resolve through the registry. No view was edited. `sdk.views.override(name,
  Component)` replaces a Core page; `sdk.views.wrap(name, Wrapper)` renders around it (the wrapper gets
  the route's props plus `original`). Both can apply to one route (the wrapper wraps the override). A
  wrapper that throws is dropped and the Core view shown. Route names are the existing router names.
- **DocType hooks.** `sdk.doctype(name).on({ defaults, onLoad, beforeSave(payload, form), afterSave(doc,
  { isNew }) })` on the generic `DocTypeForm`; `"*"` matches every doctype. A failing `beforeSave`
  stops the save and shows its message; failures in the others are logged only.
- **Form slots.** `form.<DocType>.top` and `form.<DocType>.bottom` on the generic form, with `form` and
  `doctype` passed to the component.
- Demo extension and Cypress (7 passing) cover wrap, override, hooks (including a veto) and the form slot.

Not done: the **resource registry** for list columns and form sections (`sdk.resources(...)`), the
bespoke screens that are not `DeskPage` or `DocTypeForm` (they have no slots or hooks), and a
documented policy for which route names are public API. Route names are not yet a stable contract; this
should be settled before phase 3 publishes the SDK reference.

## Phase 2b (added after review): universal coverage and dynamic settings

Raised after the phase 2 demo. Three requirements, all fitting the registry model:

1. **Every page is extendable, including bespoke ones.** Today slots come from `DeskPage`, which 120
   of 165 views use. The shell renders every route through one `<router-view>` (`DeskShell.vue`), so
   put `page.<route name>.top` and `.bottom` there instead. That covers all routes at once, with no
   per-view edit, and the `DeskPage` slots are removed so a component never renders twice.
   Pages that need a slot *inside* their layout (between sections) declare an explicit
   `<ExtensionSlot>`; those are added case by case and listed in the slot catalogue.
2. **A common contract for custom fields on bespoke forms.** The fields themselves are native Frappe
   (Custom Field fixtures from the extension app). The SDK adds the binding: a `useExtensionFields(doctype)`
   composable that a bespoke form calls once. It loads and saves the extension-owned fields into
   `form.custom`, runs the DocType hooks, and exposes the slots `form.<DocType>.<position>`, so an
   extension registers one control and it works on every bespoke form that adopts the composable. A
   customer may instead override the whole page (`views.override`, built in phase 2).
3. **Dynamic settings pages.** Settings stop being a hardcoded list in `SettingsHubView.vue`.
   - A settings page is a **Single DocType**. Core renders it with the generic `DocTypeForm`, so an
     extension that is pure Python (a Single doctype plus one hook line) gets a working settings page
     with no JavaScript.
   - Declaration, in the extension's `hooks.py`:
     `buildsuite_settings_pages = [{"doctype": "Acme Settings", "group": "Acme", "label": "...", "description": "...", "icon": "...", "roles": [...]}]`.
   - Core's backend merges its own pages with the declared ones. Each declared page is validated (the
     doctype exists and is single) and filtered by the user's DocPerms, so permissions are Frappe's, not
     a second system.
   - Route `/settings/doc/:doctype`; the hub reads the merged list. An extension that wants bespoke UI
     replaces that page's view (`views.override`) or registers its own page with `sdk.settings.addPage`.
   - Core's own settings (Core Settings, Project Settings and similar Singles) can migrate to the same
     mechanism gradually; nothing forces it.
   - Fits phase 4: a no-code editor or an AI creates a Single DocType with Frappe's own tooling and it
     appears in Settings.

   **Open item to verify first:** the generic form and `doctypeRecordApi` have no Single-DocType path
   today (read and save by doctype name). A short spike confirms it before the hub work starts.

Order: shell slots, then `useExtensionFields` on the busiest bespoke forms (Quotation, Project, Task),
then dynamic settings. Phase 3 (scaffold, docs, versioning) follows and documents all of it.

### Phase 2b status (implemented, SDK 1.2)

- **Page slots on every route.** `DeskShell` renders `page.<route name>.top` and `.bottom` around the
  `<router-view>`, so bespoke pages that do not use `DeskPage` (for example Home) are covered. The
  `DeskPage` slots were removed to avoid rendering twice. `ExtensionSlot` gained an optional wrapper.
- **`useExtensionFields(doctype, form)`.** Loads and saves an extension's Custom Fields into `custom`,
  runs the hooks, and gives the `form.<DocType>.<position>` slot names. The extension declares its
  fields with `sdk.doctype(name).on({ fields: [...] })`. Adopted by the Quotation, Project and Task create forms (slots `top` and
  `bottom`). **The other bespoke forms (Work Order, Purchase Order, Subcontractor Bill and so on) still need to adopt it**, one at a time.
- **Dynamic settings.** `buildsuite_core.sdk.get_settings_pages()` reads the `buildsuite_settings_pages`
  hook, keeping only Single DocTypes the user can read. The Settings hub lists them (plus tiles from
  `sdk.settings.addTile`) and `/settings/doc/:doctype` renders the Single with the generic form, with no
  Delete button. Verified: a Single DocType works with the generic form and `frappe.client` unchanged.
- Demo extension additions: a Single DocType and its hook, a Custom Field fixture on Quotation with its
  control, a Home page slot. 14 backend tests and 10 Cypress tests pass.

Known gaps: bespoke forms other than Quotation, Project and Task have no field binding yet (Project and Task have create forms only here; their edit screens are separate); the custom-field value was
tested as a visible, editable control, not through a full quotation save; route names are still not a
documented public contract; a settings page that is a Single DocType gets the generic layout only.

## Phase 3 status (scaffold, guide, versioning)

- Done: `bench new-buildsuite-extension <app>` (sdk/scaffold.py, commands/__init__.py, tested in
  tests/test_sdk_scaffold.py); author guide `docs/extension-sdk-guide.md` including the `min_sdk`
  rule and the route-name stability policy.
- Build config: not needed. The SDK passes Vue as `sdk.vue`, so extensions are plain ES modules.
  A Vite/SFC build with externals remains optional and unbuilt.
- Still open: a separate template repo and SDK repos (deferred until controls are extracted),
  the resource registry (list columns/sections), and phase 4.
