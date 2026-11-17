# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
	PO_PRINT_FORMAT,
	seed_print_assets,
)
from buildsuite_core.print_formats import seed_print_formats
from buildsuite_core.seed_workflows import seed_workflows

WORKFLOW = "Stage Planning Approval"


class TestSeedKeepsAdminEdits(IntegrationTestCase):
	"""A migrate re-runs the seeds; they must not overwrite what an admin changed in Desk."""

	def test_workflow_edit_survives_reseed(self):
		seed_workflows()
		wf = frappe.get_doc("Workflow", WORKFLOW)
		wf.send_email_alert = 1
		wf.save(ignore_permissions=True)
		seed_workflows()
		self.assertEqual(frappe.db.get_value("Workflow", WORKFLOW, "send_email_alert"), 1)

	def test_missing_workflow_is_created(self):
		seed_workflows()
		self.assertTrue(frappe.db.exists("Workflow", WORKFLOW))

	def test_print_format_edit_and_default_survive_reseed(self):
		seed_print_formats()
		name = "BuildSuite Quotation"
		frappe.db.set_value("Print Format", name, "html", "<p>admin edit</p>")
		frappe.make_property_setter(
			{
				"doctype": "Quotation",
				"doctype_or_field": "DocType",
				"property": "default_print_format",
				"value": "Standard",
				"property_type": "Data",
			}
		)
		seed_print_formats()
		self.assertEqual(frappe.db.get_value("Print Format", name, "html"), "<p>admin edit</p>")
		self.assertEqual(frappe.get_meta("Quotation").default_print_format, "Standard")

	def test_purchase_order_format_edit_survives_reseed(self):
		seed_print_assets()
		frappe.db.set_value("Print Format", PO_PRINT_FORMAT, "html", "<p>admin edit</p>")
		seed_print_assets()
		self.assertEqual(frappe.db.get_value("Print Format", PO_PRINT_FORMAT, "html"), "<p>admin edit</p>")
