# Extension SDK: author guide

Written for developers building an app that customises BuildSuite Core.

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

Bespoke forms that adopt `useExtensionFields`: Quotation, Project (create and edit), Task (create and edit), Work Package (create), Subcontractor Work Order and Subcontractor Bill (create and edit). Other
DocTypes use the generic form, which supports all of the above. Tell us which bespoke form
you need next.

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
