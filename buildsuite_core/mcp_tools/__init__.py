# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""MCP tool registration — one module per feature area, mirroring buildsuite_core/api/.

Importing this package (from buildsuite_core.mcp.handle_mcp) runs every submodule's
@mcp.tool() decorators, registering their tools with the MCP instance in
buildsuite_core.mcp."""

from buildsuite_core.mcp_tools import aggr
from buildsuite_core.mcp_tools import list as list_tools  # noqa: F401 — "list" shadows the builtin
