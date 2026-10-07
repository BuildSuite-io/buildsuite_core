# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Which company a tender and a quotation belong to.

The print's letter head is resolved from `company` (api.printing._letter_head_for_company), so a
document stamped with the wrong one prints the wrong branding. Both resolve it the BuildSuite
way — the project's company when there is one, else default_company(), which follows the topbar
switcher — rather than leaving it to ERPNext's global default.

NOT covered: that the switcher's choice is the one picked. On a single-company site
default_company() and ERPNext's global default are the same string, and Quotation.company is
reqd so a test cannot blank it to prove the timing. Proving either needs a second Company.
"""

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api.invoice import ensure_invoice_item
from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.project import default_company


class TestTenderCompany(BuildSuiteTestCase):
	def _tender(self, **overrides):
		payload = {
			"doctype": "BuildSuite Tenders",
			"title": "UAT bid",
			"issuing_body": "UAT Authority",
			"tender_reference": f"UAT/{frappe.generate_hash(length=5)}",
			"submission_deadline": add_days(nowdate(), 14),
			"buildsuite_tenders_items": [
				{"description": "Site supervision", "unit": "Nos", "qty": 1, "rate": 100}
			],
		}
		payload.update(overrides)
		doc = frappe.get_doc(payload)
		doc.insert(ignore_permissions=True)
		return doc

	def test_a_tender_with_no_project_takes_the_working_company(self):
		self.assertEqual(self._tender().company, default_company())

	def test_a_tender_takes_its_project_s_company(self):
		project = self._make_project()
		doc = self._tender(project=project.name)

		self.assertEqual(doc.company, project.company)

	def test_the_company_re_derives_from_the_project_on_every_save(self):
		"""anchor_company_to_project always re-derives, so a tender moved to another project's
		work cannot keep pointing at the first project's company."""
		doc = self._tender()
		project = self._make_project()

		doc.project = project.name
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.company, project.company)

	def test_a_quotation_is_stamped_with_the_working_company(self):
		"""The before_insert hook runs and leaves a company on the document."""
		customer = self._make_customer().name
		doc = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": customer,
				"title": "UAT offer",
				"items": [
					{
						"item_code": ensure_invoice_item(),
						"item_name": "Site supervision",
						"description": "Site supervision",
						"uom": "Nos",
						"qty": 1,
						"price_list_rate": 100,
					}
				],
			}
		)
		doc.insert()

		self.assertEqual(doc.company, default_company())
