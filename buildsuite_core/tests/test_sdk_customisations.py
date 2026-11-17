# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Site-level customisations: schema per kind, what is refused, and what boot receives."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.tests import IntegrationTestCase

from buildsuite_core.sdk import get_customisations
from buildsuite_core.sdk.customisations import clean_config

DT = "Crew"
FIELD = "sdk_t_site_note"


def _make(title, kind, config, **kw):
	return frappe.get_doc(
		{"doctype": "BuildSuite Customisation", "title": title, "kind": kind, "config": config, **kw}
	).insert()


class TestCustomisations(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_custom_fields({DT: [{"fieldname": FIELD, "fieldtype": "Data", "label": "Site note"}]})

	@classmethod
	def tearDownClass(cls):
		frappe.delete_doc("Custom Field", f"{DT}-{FIELD}", force=True)
		frappe.db.commit()  # the fixture's schema change must not leak
		frappe.clear_cache(doctype=DT)
		super().tearDownClass()

	# --- schema per kind -------------------------------------------------
	def test_list_column_is_normalised(self):
		out = clean_config("List Column", {"doctype": "Project", "field": "creation"})
		self.assertEqual(out["align"], "left")
		self.assertTrue(out["label"])
		out = clean_config(
			"List Column", '{"doctype": "Project", "field": "creation", "align": "right", "label": "Made"}'
		)
		self.assertEqual((out["align"], out["label"]), ("right", "Made"))

	def test_form_field_must_be_a_custom_field(self):
		out = clean_config("Form Field", {"doctype": DT, "fieldname": FIELD})
		self.assertEqual(out["position"], "bottom")
		with self.assertRaises(frappe.ValidationError):
			clean_config("Form Field", {"doctype": DT, "fieldname": "crew_name"})  # a standard field of Core

	def test_workspace_tile_and_notice(self):
		tile = clean_config(
			"Workspace Tile", {"workspace": "site-execution", "label": "Reports", "to": "/projects?x=1"}
		)
		self.assertEqual(tile["description"], "")
		note = clean_config("Notice", {"slot": "page.app-home.top", "message": "Hello"})
		self.assertEqual(note["tone"], "info")
		clean_config("Notice", {"slot": "form.Crew.bottom", "message": "Hi", "tone": "warning"})

	# --- what is refused -------------------------------------------------
	def test_unsafe_or_malformed_config_is_refused(self):
		bad = [
			("Workspace Tile", {"workspace": "site-execution", "label": "x", "to": "https://evil.example"}),
			("Workspace Tile", {"workspace": "site-execution", "label": "x", "to": "//evil.example"}),
			("Workspace Tile", {"workspace": "site-execution", "label": "x", "to": "javascript:alert(1)"}),
			("Workspace Tile", {"workspace": "site-execution", "label": "x", "to": "/../etc"}),
			("Workspace Tile", {"workspace": "Not A Slug", "label": "x", "to": "/projects"}),
			("Notice", {"slot": "anything", "message": "x"}),
			("Notice", {"slot": "page.app-home.top", "message": "x" * 501}),
			("Notice", {"slot": "page.app-home.top", "message": ""}),
			("Notice", {"slot": "page.app-home.top", "message": "x", "html": "<script>"}),  # unknown key
			("Notice", {"slot": "page.app-home.top", "message": "x", "tone": "loud"}),
			("List Column", {"doctype": "No Such DocType", "field": "x"}),
			("List Column", {"doctype": "Project", "field": "no_such_field"}),
			("List Column", [1, 2]),
			("List Column", "not json"),
			("Nonsense", {}),
		]
		for kind, config in bad:
			with self.subTest(kind=kind, config=config), self.assertRaises(frappe.ValidationError):
				clean_config(kind, config)

	# --- the record, boot, and who may write ------------------------------
	def test_record_is_validated_and_stored_clean(self):
		doc = _make("sdk t notice", "Notice", {"slot": "page.app-home.top", "message": "<b>hi</b>"})
		self.addCleanup(frappe.delete_doc, "BuildSuite Customisation", doc.name, force=True)
		stored = frappe.parse_json(frappe.db.get_value("BuildSuite Customisation", doc.name, "config"))
		self.assertEqual(stored["tone"], "info")
		self.assertEqual(stored["message"], "<b>hi</b>")  # kept as text; the SPA renders text, never HTML
		with self.assertRaises(frappe.ValidationError):
			_make("sdk t bad", "Notice", {"slot": "nope", "message": "x"})

	def test_boot_lists_enabled_only_and_describes_form_fields(self):
		on = _make("sdk t on", "Form Field", {"doctype": DT, "fieldname": FIELD, "position": "top"})
		off = _make("sdk t off", "Notice", {"slot": "page.app-home.top", "message": "x"}, enabled=0)
		self.addCleanup(frappe.delete_doc, "BuildSuite Customisation", on.name, force=True)
		self.addCleanup(frappe.delete_doc, "BuildSuite Customisation", off.name, force=True)
		by_name = {c["name"]: c for c in get_customisations()}
		self.assertNotIn(off.name, by_name)
		field = by_name[on.name]["config"]["field"]
		self.assertEqual(
			(field["fieldname"], field["fieldtype"], field["label"]), (FIELD, "Data", "Site note")
		)

	def test_a_record_that_stops_validating_is_skipped_not_fatal(self):
		doc = _make("sdk t gone", "List Column", {"doctype": "Project", "field": "creation"})
		self.addCleanup(frappe.delete_doc, "BuildSuite Customisation", doc.name, force=True)
		# A field that no longer exists, written behind the validation's back.
		frappe.db.set_value(
			"BuildSuite Customisation",
			doc.name,
			"config",
			frappe.as_json({"doctype": "Project", "field": "gone_field"}),
		)
		self.assertNotIn(doc.name, {c["name"] for c in get_customisations()})

	def test_only_a_system_manager_can_write(self):
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			_make("sdk t guest", "Notice", {"slot": "page.app-home.top", "message": "x"})
