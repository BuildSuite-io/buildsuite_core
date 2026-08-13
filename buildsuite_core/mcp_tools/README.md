# MCP tools

BuildSuite Core exposes a [Model Context Protocol](https://modelcontextprotocol.io/) server
via [`frappe-mcp`](https://github.com/frappe/mcp). The entrypoint is `buildsuite_core/mcp.py`;
tools are registered in this package, one module per feature area (mirrors `buildsuite_core/api/`).

- Endpoint: `/api/method/buildsuite_core.mcp.handle_mcp` (JSON-RPC 2.0 over `POST` only —
  a plain browser `GET` returns `405`).
- Auth: standard Frappe API key/secret (Desk → your User → API Access → Generate Keys),
  sent as `Authorization: token <api_key>:<api_secret>`. No OAuth2 setup required.
- Tools run as the calling user and are bound by the same DocPerms / permission hooks as
  the Desk and the Vue app — nothing here bypasses permissions.

## Try it with curl

```bash
curl -s -X POST http://bs.local:8000/api/method/buildsuite_core.mcp.handle_mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: token <api_key>:<api_secret>" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Try it with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Transport: Streamable HTTP. URL: the endpoint above. Add the same `Authorization` header,
then Connect → List Tools to browse and call tools interactively.

## Try it with Postman

1. Generate an API key/secret for your user: Desk → your User → **API Access** →
   **Generate Keys** (or `bench --site bs.local execute
   frappe.core.doctype.user.user.generate_keys --args '["Administrator"]'` from the bench
   shell for a local dev key).
2. New request → **MCP Request** (Postman's native MCP client; if your Postman version
   doesn't have it, use the plain HTTP fallback below instead).
3. Server URL: `http://bs.local:8000/api/method/buildsuite_core.mcp.handle_mcp`
4. Transport: **Streamable HTTP**.
5. Auth tab → **API Key** → Key: `Authorization`, Value: `token <api_key>:<api_secret>`,
   Add to: **Header**.
6. **Connect** — this runs the MCP `initialize` handshake; you should see
   `serverInfo.name: "buildsuite-core-mcp"` in the response.
7. List tools (Postman does this automatically once connected) and call one, e.g.
   `list_projects` with `{"limit": 5}`.

**No native MCP Request type?** Use a plain `POST` request instead, with the same URL and
`Authorization` header, `Content-Type: application/json`, and a raw JSON body:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
```

```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_projects", "arguments": {"limit": 5}}}
```

## Installing `frappe-mcp` on this bench

`frappe-mcp==0.1.0`'s declared `pydantic~=2.11.7` pin has no Python 3.14 wheel and fails to
build from source on this bench's Python. `pyproject.toml`'s `dependencies` pin its real
runtime deps at 3.14-compatible versions instead (`pydantic>=2.12,<3`, etc., deliberately
omitting Werkzeug so Frappe's own exact pin wins), and it's installed separately with
`--no-deps` — see the comments in `pyproject.toml`, `.devcontainer/bootstrap.sh`, and
`.github/workflows/ci.yml`.
