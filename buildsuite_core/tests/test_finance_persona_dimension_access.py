# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Finance personas can read Accounting Dimension: ERPNext's report filter scripts call a
permission-checked frappe.db.get_list on it, which otherwise surfaces "Insufficient Permission
for Accounting Dimension" in the Desk."""

import frappe

from buildsuite_core.permissions.setup import _PF_REPORT_ROLES, setup_project_finance_report_access
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestFinancePersonaDimensionAccess(BuildSuiteTestCase):
	def test_finance_personas_can_read_accounting_dimension(self):
		setup_project_finance_report_access()
		for role in _PF_REPORT_ROLES:
			self.assertTrue(
				frappe.db.exists(
					"Custom DocPerm",
					{"parent": "Accounting Dimension", "role": role, "permlevel": 0, "read": 1},
				),
				f"{role} cannot read Accounting Dimension",
			)
