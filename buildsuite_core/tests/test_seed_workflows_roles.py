# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""A fresh install seeds the shipped workflows before the BuildSuite roles exist."""

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.seed_workflows import seed_workflows

WORKFLOW = "Material Request Approval"
ROLE = "BuildSuite Procurement Officer"


class TestSeedWorkflowsCreateRoles(IntegrationTestCase):
	def test_missing_roles_are_created_so_the_workflow_inserts(self):
		# the state of a brand-new site: the workflow and the role it names are both absent
		if frappe.db.exists("Workflow", WORKFLOW):
			frappe.delete_doc("Workflow", WORKFLOW, force=True, ignore_permissions=True)
		frappe.db.delete("Has Role", {"role": ROLE})
		frappe.db.delete("Custom DocPerm", {"role": ROLE})
		frappe.db.delete("DocPerm", {"role": ROLE})
		frappe.db.delete("Role", {"name": ROLE})
		self.assertFalse(frappe.db.exists("Role", ROLE))

		seed_workflows()

		self.assertTrue(frappe.db.exists("Role", ROLE))
		self.assertTrue(frappe.db.exists("Workflow", WORKFLOW))
