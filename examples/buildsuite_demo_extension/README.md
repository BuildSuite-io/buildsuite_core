# buildsuite_demo_extension

A throwaway Frappe app that proves the BuildSuite extension SDK end to end. It is an ordinary
Frappe app; the only BuildSuite-specific part is the hook in `hooks.py`:

```python
buildsuite_frontend_extensions = [
    {"name": "buildsuite_demo_extension", "js": "/assets/buildsuite_demo_extension/js/extension.js", "min_sdk": "1.0"},
]
```

`public/js/extension.js` default-exports `register(sdk)` and adds:

| What | SDK call | Where you see it |
| --- | --- | --- |
| A page | `sdk.routes.add` | `/demo-extension` |
| A banner component | `sdk.slots.add("page.settings.top", …)` | top of the Settings page |
| A workspace tile | `sdk.workspaces.addTile("sales", …)` | Sales workspace, Reports group |
| Wrap a Core page | `sdk.views.wrap("settings-data", …)` | Settings → Data Tools gets a notice above the unchanged Core page |
| Replace a Core page | `sdk.views.override("settings-app-icon-diagnostics", …)` | that page is the extension's |
| DocType hooks and a form slot | `sdk.doctype("*").on(…)`, `sdk.slots.add("form.Account Category.top", …)` | `/records/Account Category/new`; a value containing `FORBIDDEN-DEMO` is refused on save |
| A Home page slot (bespoke page, not `DeskPage`) | `sdk.slots.add("page.app-home.top", …)` | top of Home |
| A Single DocType settings page, no JS | `buildsuite_settings_pages` in `hooks.py` | Settings → "Demo extension" group; opens at `/settings/doc/Demo Extension Settings` |
| A Custom Field on a bespoke form | Custom Field fixture + `sdk.doctype("Quotation").on({ fields })` + slot `form.Quotation.top` | Region control on the New Quotation, New Project and New Task forms |
| A deliberately broken component | `sdk.slots.add("page.settings.bottom", …)` | only when `localStorage.buildsuite_demo_break = "1"`; the Settings page must keep working |

Install: `bench get-app <path to this folder>` then `bench --site <site> install-app buildsuite_demo_extension`
and reload the SPA. Uninstall the app and all three additions disappear.
