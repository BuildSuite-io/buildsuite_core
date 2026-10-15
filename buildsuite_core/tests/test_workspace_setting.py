# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Workspace Setting — per-workspace report-style shortcut tiles."""

import json

import frappe

from buildsuite_core.api import workspace_setting as ws
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestWorkspaceSetting(BuildSuiteTestCase):
	def _set(self, workspace, rows):
		return ws.set_workspace_reports(workspace, json.dumps(rows))

	def test_explicit_route_and_external_flag(self):
		self._set(
			"subcontract",
			[
				{"label": "WO Register", "route": "/subcontractor-work-orders", "icon": "clipboard-list"},
				{"label": "Stock", "route": "/app/query-report/Stock Balance", "icon": "chart-bar"},
			],
		)
		tiles = ws.get_workspace_reports("subcontract")
		self.assertEqual(
			[t["route"] for t in tiles],
			["/subcontractor-work-orders", "/app/query-report/Stock Balance"],
		)
		# In-app path is internal; Desk URL is external.
		self.assertEqual([t["external"] for t in tiles], [False, True])
		self.assertEqual(tiles[0]["label"], "WO Register")

	def test_report_link_resolves_route_and_label(self):
		rep = frappe.get_all("Report", limit=1, pluck="name")
		self.assertTrue(rep, "expected at least one seeded Report")
		self._set("estimation", [{"report": rep[0], "icon": "file-text"}])
		tiles = ws.get_workspace_reports("estimation")
		self.assertEqual(len(tiles), 1)
		self.assertTrue(tiles[0]["route"])  # derived a Desk route from the report
		self.assertTrue(tiles[0]["label"])  # fell back to the report's name

	def test_set_replaces_only_target_workspace(self):
		self._set("subcontract", [{"label": "A", "route": "/a"}])
		self._set("procurement", [{"label": "B", "route": "/b"}])
		self._set("subcontract", [{"label": "C", "route": "/c"}])  # re-set subcontract only
		self.assertEqual([t["label"] for t in ws.get_workspace_reports("subcontract")], ["C"])
		self.assertEqual([t["label"] for t in ws.get_workspace_reports("procurement")], ["B"])

	def test_unknown_workspace_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._set("bogus", [{"label": "X", "route": "/x"}])

	def test_rows_without_destination_dropped(self):
		self._set("estimation", [{"label": "no dest", "icon": "x"}])
		self.assertEqual(ws.get_workspace_reports("estimation"), [])

	def test_erpnext_nav_toggle_defaults_off_and_round_trips(self):
		# The requirement: the ERPNext sidebar section is HIDDEN by default.
		self.assertEqual(frappe.get_meta("Workspace Setting").get_field("show_erpnext_nav").default, "0")
		# Admin turns it on, then off; the public getter reflects each change.
		self.assertTrue(ws.set_erpnext_nav_enabled(1)["show_erpnext_nav"])
		self.assertTrue(ws.get_erpnext_nav_enabled())
		self.assertFalse(ws.set_erpnext_nav_enabled(0)["show_erpnext_nav"])
		self.assertFalse(ws.get_erpnext_nav_enabled())
