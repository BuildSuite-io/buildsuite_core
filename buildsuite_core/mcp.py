# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""MCP (Model Context Protocol) server entrypoint, via the `frappe-mcp` library.

`@mcp.register()` wraps the handler in `frappe.whitelist()`, so the endpoint below
is served at /api/method/buildsuite_core.mcp.handle_mcp and authenticates exactly
like any other whitelisted method (session cookie or API key/secret) — every tool
call runs as the calling frappe.session.user and is subject to the same DocPerms /
permission_query_conditions / has_permission hooks as the Desk and the Vue app."""

import frappe_mcp

mcp = frappe_mcp.MCP("buildsuite-core-mcp")


@mcp.register()
def handle_mcp():
	import buildsuite_core.mcp_tools  # noqa: F401 — registers all @mcp.tool() functions
