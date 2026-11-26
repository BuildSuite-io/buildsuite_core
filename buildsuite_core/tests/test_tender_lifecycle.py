# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""A tender's lifecycle (Draft -> Submitted -> Under Evaluation -> Awarded / Rejected), the freeze
once it is submitted, copying to re-price, and the Tenders and Quotations lists' figures."""

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api import quotation as quotation_api
from buildsuite_core.api import tender as tender_api
from buildsuite_core.api.invoice import ensure_invoice_item
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestTenderLifecycle(BuildSuiteTestCase):
	def _tender(self, deadline_in=14, emd=0, rate=100):
		return frappe.get_doc(
			{
				"doctype": "BuildSuite Tenders",
				"title": f"UAT bid {frappe.generate_hash(length=4)}",
				"issuing_body": "UAT Authority",
				"tender_reference": f"UAT/{frappe.generate_hash(length=5)}",
				"submission_deadline": add_days(nowdate(), deadline_in),
				"emd_amount": emd,
				"buildsuite_tenders_items": [
					{"description": "Site supervision", "unit": "Nos", "qty": 1, "rate": rate}
				],
			}
		).insert(ignore_permissions=True)

	def _move(self, doc, *statuses):
		for status in statuses:
			tender_api.set_tender_status(doc.name, status)
		doc.reload()
		return doc

	# --- lifecycle ------------------------------------------------------------------------------
	def test_a_new_tender_is_a_draft(self):
		self.assertEqual(self._tender().status, "Draft")

	def test_a_tender_moves_through_its_lifecycle(self):
		doc = self._move(self._tender(), "Submitted", "Under Evaluation", "Awarded")
		self.assertEqual(doc.status, "Awarded")

	def test_a_move_the_lifecycle_does_not_allow_is_refused(self):
		doc = self._tender()
		with self.assertRaises(frappe.ValidationError):
			tender_api.set_tender_status(doc.name, "Awarded")  # a draft is not decided yet
		self._move(doc, "Submitted", "Rejected")
		with self.assertRaises(frappe.ValidationError):
			tender_api.set_tender_status(doc.name, "Awarded")
		self.assertEqual(self._move(doc, "Draft").status, "Draft")  # a lost bid can be reopened

	def test_the_status_is_not_set_by_editing(self):
		doc = self._tender()
		doc.status = "Awarded"
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_a_submitted_tender_is_frozen(self):
		doc = self._move(self._tender(), "Submitted")
		doc.margin_percent = 30
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_an_awarded_tender_cannot_be_deleted(self):
		doc = self._move(self._tender(), "Submitted", "Awarded")
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("BuildSuite Tenders", doc.name)

	def test_copy_to_reprice_is_an_editable_draft(self):
		src = self._move(self._tender(), "Submitted")
		copy = frappe.get_doc("BuildSuite Tenders", tender_api.copy_tender(src.name)["name"])
		self.assertEqual(copy.status, "Draft")
		self.assertEqual(copy.title, f"{src.title} (revised)")
		self.assertEqual(len(copy.buildsuite_tenders_items), 1)
		copy.margin_percent = 30
		copy.save()  # not frozen

	# --- the Tenders list's figures ---------------------------------------------------------------
	def test_tender_kpis(self):
		before = tender_api.tender_kpis()
		due = self._tender(deadline_in=3, emd=500)
		self._tender(deadline_in=30, emd=200)
		self._move(self._tender(emd=1000), "Submitted")
		won = self._move(self._tender(rate=400), "Submitted", "Awarded")
		self._move(self._tender(emd=900), "Submitted", "Rejected")

		k = tender_api.tender_kpis()
		self.assertEqual(k["in_play"] - before["in_play"], 3)
		# earnest money on drafts and submitted bids only: a decided bid's EMD has come back
		self.assertEqual(k["emd_at_stake"] - before["emd_at_stake"], 1700)
		self.assertEqual(k["awarded_value"] - before["awarded_value"], won.bid_value)
		self.assertIn(due.name, [d["name"] for d in k["due_soon"]])
		if not before["win_rate"] and before["total"] == 0:
			self.assertEqual(k["win_rate"], 50)  # one awarded of two decided

	def test_win_rate_is_none_when_nothing_is_decided(self):
		if tender_api.tender_kpis()["total"]:
			self.skipTest("the site has tenders of its own")
		self._tender()
		self.assertIsNone(tender_api.tender_kpis()["win_rate"])


class TestQuotationKpis(BuildSuiteTestCase):
	def _sent_quotation(self, valid_till=None):
		customer = self._make_customer()
		doc = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": customer.name,
				"title": "UAT offer",
				"valid_till": valid_till or add_days(nowdate(), 30),
				"items": [
					{
						"item_code": ensure_invoice_item(),
						"description": "Site supervision",
						"uom": "Nos",
						"qty": 1,
						"price_list_rate": 1000,
						"rate": 1000,
					}
				],
			}
		).insert()
		quotation_api.send_quotation(doc.name)
		doc.reload()
		return doc

	def test_quotation_kpis(self):
		before = quotation_api.quotation_kpis()
		waiting = self._sent_quotation()
		won = self._sent_quotation()
		quotation_api.accept_quotation(won.name)
		lost = self._sent_quotation()
		quotation_api.reject_quotation(lost.name, detailed_reason="Too dear")

		k = quotation_api.quotation_kpis()
		self.assertAlmostEqual(k["awaiting_value"] - before["awaiting_value"], waiting.base_grand_total)
		self.assertAlmostEqual(k["won_value"] - before["won_value"], won.base_grand_total)
		self.assertIsNotNone(k["win_rate"])

	def test_a_sent_quotation_past_its_validity_is_counted(self):
		before = quotation_api.quotation_kpis()["past_validity"]
		q = self._sent_quotation()
		frappe.db.set_value("Quotation", q.name, "valid_till", add_days(nowdate(), -1))
		self.assertEqual(quotation_api.quotation_kpis()["past_validity"] - before, 1)
