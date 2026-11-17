"""Workspace shortcuts no longer carry their own "Restrict To Roles" list: who sees a shortcut
follows Frappe permissions on what it opens (read on the DocType behind its route, or a report's
roles — api.workspace_setting.get_workspace_shortcuts). The field is gone from the doctype; this
removes the restriction rows it leaves behind, which nothing reads any more.

Only those rows are touched: no DocPerm, no workspace "Visible To" role, no shortcut itself.
A role that should (or should not) see a shortcut is now given that in Role Permission Manager."""

import frappe


def execute():
	frappe.db.delete("BuildSuite Workspace Role", {"parenttype": "BuildSuite Workspace Shortcut"})
