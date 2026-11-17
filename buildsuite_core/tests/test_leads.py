# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Sales > Leads — enquiries on ERPNext's own Lead, quoted as drafts, converted to customers.

What matters is the rule the board and the quotation form rely on: a lead's status follows its
DRAFT quotations (ERPNext alone only counts submitted ones, and would reset the lead to Open on
every save), and converting it makes a customer that the lead's quotations move to.
"""

import frappe

from buildsuite_core.api import leads as api
from buildsuite_core.api.invoice import ensure_invoice_item
from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.lead import mobile_key, mobile_matches


class TestLeads(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.item = ensure_invoice_item()
		# Ten digits that no fixture uses, so dedupe only ever finds what the test made.
		self.mobile = "+91 9" + str(int(frappe.generate_hash(length=6), 16) % 10**9).zfill(9)

	def _lead(self, **values):
		values.setdefault("first_name", f"UAT {self._n}")
		return api.create_lead(**values)["name"]

	def _quote(self, lead):
		doc = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Lead",
				"party_name": lead,
				"title": "UAT offer",
				"items": [
					{
						"item_code": self.item,
						"item_name": "Site supervision",
						"description": "Site supervision",
						"uom": "Nos",
						"qty": 1,
						"price_list_rate": 500,
						"margin_type": "Percentage",
						"margin_rate_or_amount": 0,
						"source": "Manual",
					}
				],
			}
		)
		doc.insert()
		return doc

	def _status(self, lead):
		return frappe.db.get_value("Lead", lead, "status")

	# --- adding -------------------------------------------------------------
	def test_a_lead_needs_a_person_or_an_organisation(self):
		with self.assertRaises(frappe.ValidationError):
			api.create_lead(first_name="", company_name="")

	def test_a_new_lead_starts_in_lead_owned_by_whoever_adds_it(self):
		name = self._lead(company_name="Siddiqui Textiles")
		doc = frappe.get_doc("Lead", name)
		self.assertEqual(doc.status, "Lead")
		self.assertEqual(doc.lead_owner, "Administrator")
		self.assertTrue(doc.company)
		# The organisation is the name quotations and the customer will carry.
		self.assertEqual(api.get_lead(name)["lead"]["party_name"], "Siddiqui Textiles")

	def test_a_new_lead_cannot_start_in_a_system_status(self):
		name = self._lead(status="Converted")
		self.assertEqual(self._status(name), "Lead")

	# --- the same person again ----------------------------------------------
	def test_mobile_key_ignores_spaces_and_the_country_code(self):
		self.assertEqual(mobile_key("+91 98471 20101"), "9847120101")
		self.assertEqual(mobile_key("098471-20101"), "9847120101")
		self.assertEqual(mobile_key("12345"), "")

	def test_the_same_mobile_written_differently_is_found(self):
		first = self._lead(mobile_no=self.mobile)
		digits = self.mobile.replace(" ", "").replace("+91", "")
		matches = mobile_matches(digits)
		self.assertIn(first, [m["id"] for m in matches if m["kind"] == "Lead"])
		# A lead is never its own duplicate.
		self.assertNotIn(first, [m["id"] for m in mobile_matches(digits, except_lead=first)])

	# --- status follows the quotations ----------------------------------------
	def test_a_draft_quotation_moves_the_lead_to_quotation(self):
		lead = self._lead()
		self._quote(lead)
		self.assertEqual(self._status(lead), "Quotation")

	def test_saving_the_lead_keeps_the_status_its_draft_quotation_gave_it(self):
		# ERPNext's own set_status only counts SUBMITTED quotations and would put this back to Open.
		lead = self._lead()
		self._quote(lead)
		api.update_lead(lead, last_name="Varghese")
		self.assertEqual(self._status(lead), "Quotation")

	def test_deleting_the_last_quotation_hands_the_lead_back_to_open(self):
		lead = self._lead()
		quotation = self._quote(lead)
		frappe.delete_doc("Quotation", quotation.name)
		self.assertEqual(self._status(lead), "Open")

	def test_a_quoted_lead_takes_do_not_contact_but_no_other_hand_status(self):
		lead = self._lead()
		self._quote(lead)
		with self.assertRaises(frappe.ValidationError):
			api.update_lead(lead, status="Interested")
		api.update_lead(lead, status="Do Not Contact")
		self.assertEqual(self._status(lead), "Do Not Contact")
		# Taking it back hands it to its quotations again.
		api.update_lead(lead, status="Open")
		self.assertEqual(self._status(lead), "Quotation")

	def test_a_lead_with_quotations_cannot_be_deleted(self):
		lead = self._lead()
		self._quote(lead)
		with self.assertRaises(frappe.ValidationError):
			api.delete_lead(lead)

	# --- conversion ---------------------------------------------------------
	def test_converting_makes_a_customer_and_moves_the_quotations_to_it(self):
		lead = self._lead(company_name=f"UAT Bakers {self._n}", mobile_no=self.mobile)
		quotation = self._quote(lead)

		out = api.convert_lead(lead)

		self.assertFalse(out["linked"])
		customer = frappe.get_doc("Customer", out["customer"])
		self.assertEqual(customer.lead_name, lead)
		self.assertEqual(customer.customer_type, "Company")
		self.assertEqual(self._status(lead), "Converted")
		moved = frappe.db.get_value("Quotation", quotation.name, ["quotation_to", "party_name"], as_dict=True)
		self.assertEqual((moved.quotation_to, moved.party_name), ("Customer", customer.name))
		# The lead's page now lists the customer's quotations.
		self.assertEqual([q.name for q in api.get_lead(lead)["quotations"]], [quotation.name])
		# Its own customer shares its mobile, but is not "another record on file".
		self.assertEqual(api.get_lead(lead)["mobile_matches"], [])
		# Converting twice does nothing new.
		self.assertTrue(api.convert_lead(lead)["existing"])

	def test_a_customer_with_the_same_mobile_is_linked_not_duplicated(self):
		customer = self._make_customer()
		customer.db_set("mobile_no", self.mobile)
		lead = self._lead(mobile_no=self.mobile)

		out = api.convert_lead(lead)

		self.assertTrue(out["linked"])
		self.assertEqual(out["customer"], customer.name)
		self.assertEqual(frappe.db.get_value("Customer", customer.name, "lead_name"), lead)
		self.assertEqual(self._status(lead), "Converted")

	def test_a_role_that_cannot_create_customers_cannot_convert(self):
		lead = self._lead()
		user = self._make_user_with_role("BuildSuite QS")
		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.PermissionError):
				api.convert_lead(lead)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(self._status(lead), "Lead")

	def _make_user_with_role(self, role):
		email = f"uat-lead-{self._n}@example.com"
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "UAT", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		user.add_roles(role)
		return email
