# Review of the current implementation: `feat/app-extension-hooks`

Purpose: a factual record of the issues in the existing branch, as input for the alternative design in
[extension-sdk-plan.md](extension-sdk-plan.md).

- Reviewed: commit `31bbd3f` ("wip: frontend extension hooks for installed apps", 2026-11-10), 13 files, +297/−9,
  against `develop` at `820e2ae`.
- Method: code reading of the diff only. **The branch was not built or run**, so items are marked
  *observed* (visible in the code) or *expected* (follows from the code but untested).
- The branch has a clear and useful starting idea (let another app extend the SPA). Several pieces
  are worth keeping (last section). The issues below are mostly about scope and architecture, not effort.

## 1. Fit against the stated goal

The goal: a generic mechanism where a user's own Frappe app, created from a template, customises
workspaces, adds and overrides pages, and later can be driven from a no-code or AI editor.

| Capability wanted | Status in the branch | Evidence |
| --- | --- | --- |
| App created from a template | **Absent**: no template, scaffold, docs or example extension in the branch | no such files in the diff |
| Customise workspaces | **Absent**: the API has no workspace operation | `registerDocExtension`, `registerSettingsTile`, `addRoute` are the only calls |
| Add pages | Present | `addRoute` into a new named `shell` route |
| Override existing pages | **Absent**: no replace or wrap mechanism; a route at an existing path does not reliably displace Core's | `extensions/index.js` |
| Extend forms | **Partial**: hardcoded to Quotation (4 positions) and Assembly (1) | `NewQuotationView.vue`, `QuotationDetailView.vue`, `AssemblyDetailView.vue` |
| Custom fields | **Partial**: only wired on the Quotation form (`form.custom`) | `NewQuotationView.vue` |
| Site-level or AI/drag-and-drop customisation | **Absent**, and the design (JS files compiled into Core) points away from it | `import.meta.glob` build-time bundling |

The shape (code-in-sibling-app, hand-placed slots) is a **developer extension API for the pages the
author needed**, which matches the observation that it targets a specific customer's requirement.

## 2. Architectural issues

1. **Build-time coupling to other apps.** `import.meta.glob("../../../../*/buildsuite_extension/index.js", { eager: true })`
   makes Core's build read every sibling app on the bench. *Observed.* Consequences:
   - a broken or missing-dependency sibling extension can fail Core's build *(expected)*;
   - Core cannot be built or released independently of what else sits on the bench;
   - the Tailwind `content` list and Vite `server.fs.allow` are widened to the whole apps folder.
2. **Extension code ships to sites that do not have the app.** `eager: true` puts every extension in
   the bundle; "installed" is checked only at runtime (`window.installed_apps`). *Observed.* The
   customer-specific code is therefore delivered to, and downloaded by, every site's users.
3. **Frappe already knows which apps are installed.** The branch adds a boot key `installed_apps` and
   a path-parsing step (`path.split("/").slice(-3)[0]`) to rediscover it. Declaring the entry in the
   extension's `hooks.py` and reading `frappe.get_hooks` gives installed-only gating for free and
   needs no build-time glob. *Observed.*
4. **No public contract or versioning.** Extension files import Core's modules through `@/…`
   (stated in the file header). Every Core refactor can silently break extensions; there is no SDK
   version, no `min_sdk`, no stability promise. *Observed.*
5. **Extension points are hand-placed per page.** Each extendable page needs edits in Core: slot
   markup, an `extensionSections(...)` call, and doc comments. Quotation and Assembly are done; every
   other page has none. *Observed.* This does not scale to "customise any page" and bakes doctype
   names ("Quotation", "Assembly") into the generic loader's documentation and call sites.
6. **Weak failure isolation.** Registration is wrapped in try/catch, but extension components render
   inside Core pages with no error boundary; a component that throws at render can break the host
   page. Hook failures (`beforeSave`) abort the save with only a generic toast. *Expected.*
7. **Registry is module-global and non-reactive.** `DOCS` and `TILES` are plain objects and arrays;
   sections are read once at component setup (`const extraSections = extensionSections(...)`). That
   works only because registration completes before mount. Later registration (a lazy extension, a
   site-level layer) would not be picked up. *Observed.*
8. **Duplicate and ordering rules are thin.** Doc extensions de-duplicate only by an optional `key`;
   tiles by `slug`. There is no ordering, priority or conflict rule between two extensions on the
   same doctype or slot, and no way for a site to disable one. *Observed.*
9. **Shared runtime by `dedupe`.** `resolve.dedupe: ["vue","vue-router","pinia","frappe-ui"]` makes
   extensions share Core's copies only when their source is compiled inside Core's build. An
   independently built extension app (the template scenario) has no way to share them. *Observed.*
10. **Information exposure.** Boot now returns the full list of installed apps to every signed-in
    user. Low risk but unintentional surface. *Observed.*
11. **Hooks are not asynchronous-safe at the seams.** `defaults(form)` is invoked without awaiting
    at setup; `afterSave` runs after the document is stored but before navigation, so its failure
    shows "Could not save" for a record that did save. *Expected.*

## 3. Defects and risks in the bundled changes

The commit mixes unrelated changes under a "wip" message, and no tests are added. Items 2 to 5 are not
part of the extension mechanism.

1. **No tests, one wip commit.** The only commit message says "Snapshot of the uncommitted work".
2. **`RichTextEditor.vue`: edits can be silently dropped.** `onChange` ignores a change unless
   `root.contains(document.activeElement)`. frappe-ui's colour picker and some toolbar menus render
   in a popover outside that element, so a change made there would not emit. *Expected; untested.*
   The change is also unrelated to extensions.
3. **`ConstructionRateMaster.on_update` reprices every assembly synchronously.** It loads and saves
   each assembly that uses the resource inside the web request. A rate used by many assemblies makes
   the save slow, and one assembly failing validation blocks the rate save. *Observed.* Also an
   unrelated behaviour change with no test.
4. **Assembly "Duplicate" feature.** Unrelated to extensions. `freeCode` makes up to 99 sequential
   `get_count` requests to find a free code and is race-prone; it copies custom fields wholesale
   through a deny-list (`DUPLICATE_SKIP`), so a new field type or system field is copied by default.
   *Observed.*
5. **`?category=` filter on the Assemblies list.** Unrelated, small.
6. **Formatting.** Long single-line `<component>` tags and a one-line `DUPLICATE_SKIP` set; the
   project's pre-commit prettier would reformat them. *Observed.*
7. **Comment claims not backed by tests.** e.g. "Estimates and quotations keep the snapshot they
   took", relied on by the repricing change, is not asserted anywhere. *Observed.*

## 4. Comparison summary (for the presentation)

| Dimension | `feat/app-extension-hooks` | Proposed SDK plan |
| --- | --- | --- |
| Discovery | build-time glob + runtime `installed_apps` | Frappe hook, installed apps only |
| Packaging | extension code compiled into Core's bundle | extension builds its own bundle, loaded at runtime |
| Build independence | Core build depends on sibling apps | none |
| Public contract | none (`@/` imports) | versioned JS SDK + Python SDK |
| Extension points | hand-placed on 2 doctypes | named registries, generic `<ExtensionSlot>` everywhere |
| Override pages | no | `views.override` / `views.wrap` |
| Workspaces | no | registry API |
| Template / scaffold | no | template + `new-extension` |
| No-code / AI path | no | declarations as data, site-level layer (phase 4) |
| Failure isolation | try/catch at registration | per-extension isolation + error boundary |
| Tests | none | per-phase tests, fixture extension |

## 5. What is worth keeping

- The named `shell` route so an extension can add pages inside the app shell.
- The idea and shape of the document hooks: `defaults`, `onLoad`, `beforeSave`, `afterSave`.
- The recognition that extension components need Core's Vue, router and store as a single instance.
- The wish to carry an app's Custom Fields through a form (the mechanism needs to be generic, not
  Quotation-only).
