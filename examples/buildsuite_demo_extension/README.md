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
| A deliberately broken component | `sdk.slots.add("page.settings.bottom", …)` | only when `localStorage.buildsuite_demo_break = "1"`; the Settings page must keep working |

Install: `bench get-app <path to this folder>` then `bench --site <site> install-app buildsuite_demo_extension`
and reload the SPA. Uninstall the app and all three additions disappear.
