# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""The quotation lifecycle on top of Sales > Leads: send, accept (converts the lead), reject with
a reason; the offer-status labels and list filters; lead notes on ERPNext's CRM Note table; and a
project needing a real customer behind the winning quotation."""

import frappe

from buildsuite_core.api import leads as lead_api
from buildsuite_core.api import quotation as quotation_api
from buildsuite_core.api.invoice import ensure_invoice_item
from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.quotation import OFFER_STATUS_FILTERS, OFFER_STATUSES, offer_status


class TestQuotationLifecycle(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.item = ensure_invoice_item()
		frappe.db.delete("Item Price", {"item_code": self.item})
		# Ten digits that no fixture uses, so a conversion never links someone else's customer.
		self.mobile = "+91 9" + str(int(frappe.generate_hash(length=6), 16) % 10**9).zfill(9)

	def _lead(self, **values):
		values.setdefault("first_name", f"UAT {self._n}")
		values.setdefault("mobile_no", self.mobile)
		return frappe.get_doc("Lead", lead_api.create_lead(**values)["name"])

	def _quotation(self, lead):
		doc = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Lead",
				"party_name": lead.name,
				"title": "UAT offer",
				"items": [
					{
						"item_code": self.item,
						"item_name": "Site supervision",
						"description": "Site supervision",
						"uom": "Nos",
						"qty": 2,
						"price_list_rate": 500,
					}
				],
			}
		)
		doc.insert()
		return doc

	# --- the quotation moves the lead --------------------------------------------------
	def test_sending_a_quotation_puts_the_lead_in_quotation(self):
		lead = self._lead()
		q = self._quotation(lead)
		self.assertEqual(offer_status(q.docstatus, q.status, q.accepted_on), "Draft")
		quotation_api.send_quotation(q.name)
		q.reload()
		self.assertEqual(offer_status(q.docstatus, q.status, q.accepted_on), "Sent")
		self.assertEqual(frappe.db.get_value("Lead", lead.name, "status"), "Quotation")

	def test_accepting_converts_the_lead_and_labels_the_offer_accepted(self):
		lead = self._lead()
		q = self._quotation(lead)
		quotation_api.send_quotation(q.name)
		res = quotation_api.accept_quotation(q.name)
		q.reload()
		self.assertEqual(offer_status(q.docstatus, q.status, q.accepted_on), "Accepted")
		self.assertEqual(frappe.db.get_value("Lead", lead.name, "status"), "Converted")
		self.assertEqual(frappe.db.get_value("Customer", res["customer"], "lead_name"), lead.name)
		with self.assertRaises(frappe.ValidationError):
			quotation_api.accept_quotation(q.name)

	def test_accepting_a_draft_is_refused(self):
		q = self._quotation(self._lead())
		with self.assertRaises(frappe.ValidationError):
			quotation_api.accept_quotation(q.name)

	def test_rejecting_needs_a_reason_and_leaves_the_lead_lost(self):
		lead = self._lead()
		q = self._quotation(lead)
		quotation_api.send_quotation(q.name)
		with self.assertRaises(frappe.ValidationError):
			quotation_api.reject_quotation(q.name)
		reason = frappe.get_doc(
			{"doctype": "Quotation Lost Reason", "order_lost_reason": f"Too dear {self._n}"}
		).insert(ignore_permissions=True)
		quotation_api.reject_quotation(
			q.name, frappe.as_json([reason.name]), None, "Went with a cheaper builder"
		)
		q.reload()
		self.assertEqual(offer_status(q.docstatus, q.status, q.accepted_on), "Rejected")
		self.assertEqual([r.lost_reason for r in q.lost_reasons], [reason.name])
		self.assertEqual(frappe.db.get_value("Lead", lead.name, "status"), "Lost Quotation")

	def test_an_accepted_offer_cannot_be_rejected(self):
		q = self._quotation(self._lead())
		quotation_api.send_quotation(q.name)
		quotation_api.accept_quotation(q.name)
		with self.assertRaises(frappe.ValidationError):
			quotation_api.reject_quotation(q.name, None, None, "changed our minds")

	def test_accepted_survives_the_expiry_job(self):
		q = self._quotation(self._lead())
		quotation_api.send_quotation(q.name)
		quotation_api.accept_quotation(q.name)
		frappe.db.set_value("Quotation", q.name, "status", "Expired")  # what ERPNext's daily job does
		q.reload()
		self.assertEqual(offer_status(q.docstatus, q.status, q.accepted_on), "Accepted")

	def test_status_labels_and_filters_come_from_one_table(self):
		self.assertEqual(set(OFFER_STATUS_FILTERS), set(OFFER_STATUSES))
		lead = self._lead()
		sent = self._quotation(lead)
		quotation_api.send_quotation(sent.name)
		won = self._quotation(lead)
		quotation_api.send_quotation(won.name)
		quotation_api.accept_quotation(won.name)
		draft = self._quotation(lead)
		for label in OFFER_STATUSES:
			names = set(frappe.get_all("Quotation", filters=OFFER_STATUS_FILTERS[label], pluck="name"))
			for q in (draft, sent, won):
				row = frappe.db.get_value(
					"Quotation", q.name, ["docstatus", "status", "accepted_on"], as_dict=True
				)
				self.assertEqual(
					q.name in names,
					offer_status(row.docstatus, row.status, row.accepted_on) == label,
					f"{label}: filter and label disagree on {q.name}",
				)

	# --- notes (ERPNext's CRM Note table) ----------------------------------------------
	def test_notes_are_added_edited_and_deleted(self):
		lead = self._lead()
		[note] = lead_api.add_note(lead.name, "<p>Wants a two-storey house</p>")
		self.assertEqual(note["added_by"], frappe.session.user)
		[edited] = lead_api.edit_note(lead.name, str(note["name"]), "<p>Wants a three-storey house</p>")
		self.assertIn("three-storey", edited["note"])
		self.assertEqual([n["name"] for n in lead_api.get_lead(lead.name)["notes"]], [note["name"]])
		self.assertEqual(lead_api.delete_note(lead.name, str(note["name"])), [])
		with self.assertRaises(frappe.ValidationError):
			lead_api.add_note(lead.name, "  ")

	# --- a project needs a customer ---------------------------------------------------
	def test_a_project_cannot_be_made_from_a_quotation_to_an_unconverted_lead(self):
		from buildsuite_core.api.boq import _customer_of_won_quotation

		lead = self._lead()
		q = self._quotation(lead)
		won = {"doctype": "Quotation", "name": q.name}
		with self.assertRaises(frappe.ValidationError):
			_customer_of_won_quotation(won)
		quotation_api.send_quotation(q.name)
		res = quotation_api.accept_quotation(q.name)
		self.assertEqual(_customer_of_won_quotation(won), res["customer"])

	def test_a_quotation_to_a_customer_names_that_customer(self):
		from buildsuite_core.api.boq import _customer_of_won_quotation

		customer = self._make_customer()
		q = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": customer.name,
				"title": "UAT offer",
				"items": [
					{
						"item_code": self.item,
						"item_name": "x",
						"description": "x",
						"uom": "Nos",
						"qty": 1,
						"price_list_rate": 1,
					}
				],
			}
		).insert()
		self.assertEqual(_customer_of_won_quotation({"doctype": "Quotation", "name": q.name}), customer.name)
		self.assertIsNone(_customer_of_won_quotation({"doctype": "BuildSuite Tenders", "name": "x"}))

	def test_accepting_without_the_right_to_create_customers_leaves_the_lead_waiting(self):
		lead = self._lead()
		q = self._quotation(lead)
		quotation_api.send_quotation(q.name)
		original = frappe.has_permission

		def deny_customer_create(doctype=None, ptype=None, *a, **kw):
			if doctype == "Customer" and ptype == "create":
				return False
			return original(doctype, ptype, *a, **kw)

		frappe.has_permission = deny_customer_create
		try:
			res = quotation_api.accept_quotation(q.name)
		finally:
			frappe.has_permission = original
		q.reload()
		self.assertIsNone(res["customer"])
		self.assertEqual(offer_status(q.docstatus, q.status, q.accepted_on), "Accepted")
		self.assertNotEqual(frappe.db.get_value("Lead", lead.name, "status"), "Converted")
