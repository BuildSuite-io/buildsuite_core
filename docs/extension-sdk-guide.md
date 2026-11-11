# Extension SDK: author guide

Written for developers building an app that customises BuildSuite Core.

A one-page visual walkthrough is in [extension-sdk-quickstart.html](extension-sdk-quickstart.html); open it in a browser.

## Start

    bench new-buildsuite-extension acme_ext --title "Acme Extension"
    bench get-app ./acme_ext && bench --site <site> install-app acme_ext

The app declares one hook and ships one ES module. Reload the browser after editing
`public/js/extension.js`; no frontend build is needed because Vue arrives as `sdk.vue`.

## What you can do

| Goal | API (in `register(sdk)`) |
| --- | --- |
| Add a page | `sdk.routes.add(...)` |
| Add content to any page | `sdk.slots.add("page.<route name>.top" \| ".bottom", Component)` |
| Add content to a generic DocType form | `sdk.slots.add("form.<DocType>.top" \| ".bottom", Component)` |
| Add a workspace tile | `sdk.workspaces.addTile(...)` |
| Wrap or replace a Core page | `sdk.views.wrap(name, Component)` / `sdk.views.override(name, Component)` |
| React to a DocType form | `sdk.doctype(dt).on({ defaults, onLoad, beforeSave, afterSave })` |
| Carry Custom Fields through a bespoke form | `sdk.doctype(dt).on({ fields: [...] })` plus a control in the `form.<DocType>.top/bottom` slot |
| Add a column to a list | `sdk.doctype(dt).on({ listColumns: [{ field, label, align?, render?(value, row) }] })` |
| Add a settings page | hook `buildsuite_settings_pages` (a Single DocType) |

A failing extension is isolated: its error is logged and the rest of the app keeps working.

## Versioning and stability

- `sdk.version` / `SDK_VERSION` is `major.minor`. The minor grows when the surface only grows;
  the major changes when something is removed or changes meaning.
- Declare `min_sdk` in your hook entry. An extension whose `min_sdk` is newer than the running
  Core is skipped with a console warning instead of loading half-working.
- **Route names** (`page.<name>.*`, `views.override(<name>)`) are part of the public surface:
  Core renames one only with a major SDK bump.
- Everything not reachable through `sdk` (for example `@/` imports) is private and may change.

## Forms that accept Custom Fields

Every bespoke create form now adopts `useExtensionFields`: Quotation, Project, Task, Work Package,
Subcontractor Work Order, Subcontractor Bill, Machinery, Machinery Usage, Scope Change Order, Stage Planning,
Task Progress Entry, Tender, Crew, Field Attendance, Field Employee, Subcontractor, Material Consumption,
Measurement Book, Assembly and Estimate Template. The edit screens of Project and Task do too, and the
forms that also edit (Quotation, Tender, Work Order, Bill, Consumption, Measurement Book) load saved values.

The registry key is the DocType that stores the record, which is not always the screen's name: Field Employee
saves an `Employee`, Subcontractor a `Supplier`, Material Consumption a `Stock Entry`. Register against that.
A Custom Field on `Employee`, `Supplier` or `Stock Entry` is a field of that DocType everywhere, not only on the
BuildSuite screen.

## Bespoke save APIs and Custom Fields

A bespoke form saves through a whitelisted function that copies named fields, so a Custom Field would
be dropped unless the function opts in. Core's helpers do that safely
(`buildsuite_core.sdk.custom_fields`):

- `apply_custom_fields(doc, values)` before `doc.save()`: sets a value only if the key is a Custom Field of
  that DocType, a plain value field, not read-only, and the user can write its permission level. A
  standard field (`owner`, `docstatus`, amounts) is never set through it.
- `custom_field_values(doc)` when serializing: the values the form binds back for editing.

The SPA sends them as `custom_fields` (a JSON string for type-checked functions).

### Edit screens

An edit modal on a detail page works the same way, with two extra steps: the detail view adds
`docFields(<DocType>)` to the fields it reads (so the values come back) and calls `ext.load(...)` when the
modal opens. These save through the generic resource update, so no backend change is needed.

## List columns

`listColumns` adds a column to every list of that DocType that is built on `DocTypeListView` or passes
`filter-doctype` / `ext-doctype` to `DeskList`. The values are not on the rows the list was given, so
`DeskList` reads them for the rows on screen in one query (by document name, up to 500 rows at a time);
rows must therefore be keyed by the document name. A column whose `field` Core already shows is skipped.
The column can be sorted from the list's sort control. It cannot be filtered or used for server-side
sorting yet.

## Site-level customisations (no code, no app)

A **BuildSuite Customisation** record (System Manager only) customises one site as data. Core validates the
record on save and merges it into the same registries an installed app uses, after the apps, so for
anything where order matters the site wins over an app and an app over Core.

| Kind | Config | Effect |
| --- | --- | --- |
| List Column | `{doctype, field, label?, align?}` | a column on that DocType's lists |
| Form Field | `{doctype, fieldname, position?}` | a control, drawn from the Custom Field's meta, on a bespoke form |
| Workspace Tile | `{workspace, label, to, description?}` | a tile on a workspace |
| Notice | `{slot, message, tone?}` | a plain-text notice in a slot such as `page.app-home.top` |

Rules the server enforces: unknown keys are refused; `to` must be a path inside the app; a notice is text,
never HTML; a Form Field must name a **Custom Field** (create it first with Frappe's own tooling), never a
standard field. A record that stops validating later (a field deleted) is skipped, not fatal.

A Form Field control appears on the bespoke forms that adopted `useExtensionFields`; the generic DocType form
already shows every Custom Field itself. Do not declare the same field both in an app and on the site: it
would get two controls.

The same data can be written by a person in the Desk list, or by an AI or a drag-and-drop editor through
the normal document API, and it takes effect on the next page load.
