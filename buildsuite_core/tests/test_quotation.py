# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Estimation › Quotations — the Vue front-end over ERPNext's Quotation: the summary cards,
saving a draft, and moving it along once it has gone out."""

import json

import frappe
from frappe.utils import add_days, flt, nowdate

from buildsuite_core.api import quotation as api
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestQuotation(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.customer = self._make_customer().name

	# --- builders --------------------------------------------------------
	def _save(self, **overrides):
		payload = {
			"party_name": self.customer,
			"title": "UAT offer",
			"items": [{"description": "Site supervision", "uom": "Nos", "qty": 2, "rate": 500}],
		}
		payload.update(overrides)
		return api.save_quotation(json.dumps(payload))["name"]

	def _submitted(self):
		name = self._save()
		api.mark_sent(name)
		return name

	# --- saving by hand --------------------------------------------------
	def test_save_creates_a_draft_with_the_typed_lines(self):
		doc = frappe.get_doc("Quotation", self._save())

		self.assertEqual(doc.docstatus, 0)
		self.assertEqual(doc.quotation_to, "Customer")
		self.assertEqual(doc.party_name, self.customer)
		self.assertEqual(len(doc.items), 1)

		line = doc.items[0]
		# Free text hangs off the shared service item; the description carries the real text.
		self.assertEqual(line.item_code, "Professional Services")
		self.assertEqual(line.item_name, "Site supervision")
		self.assertEqual(line.source, "Manual")
		self.assertEqual(flt(line.amount), 1000)

	def test_save_defaults_the_issue_date_and_keeps_a_given_one(self):
		self.assertEqual(str(frappe.get_doc("Quotation", self._save()).transaction_date), nowdate())

		dated = self._save(transaction_date="2026-03-01", valid_till="2026-04-01")
		doc = frappe.get_doc("Quotation", dated)
		self.assertEqual(str(doc.transaction_date), "2026-03-01")
		self.assertEqual(str(doc.valid_till), "2026-04-01")

	def test_save_rejects_a_quotation_with_no_customer_or_no_lines(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(party_name="")
		with self.assertRaises(frappe.ValidationError):
			self._save(items=[])

	def test_save_names_the_row_whose_description_is_missing(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			self._save(
				items=[
					{"description": "Fine", "qty": 1, "rate": 1},
					{"description": "   ", "qty": 1, "rate": 1},
				]
			)
		self.assertIn("Row 2", str(caught.exception))

	def test_save_replaces_the_lines_of_a_draft_rather_than_appending(self):
		name = self._save()
		self._save(
			name=name,
			items=[
				{"description": "One", "qty": 1, "rate": 10},
				{"description": "Two", "qty": 1, "rate": 20},
			],
		)
		doc = frappe.get_doc("Quotation", name)
		self.assertEqual([line.item_name for line in doc.items], ["One", "Two"])

	def test_an_unknown_uom_is_rejected_rather_than_silently_dropped(self):
		with self.assertRaises(frappe.LinkValidationError):
			self._save(items=[{"description": "x", "uom": "furlong", "qty": 1, "rate": 1}])

	# --- moving it along --------------------------------------------------
	def test_mark_sent_submits_and_freezes_the_quotation(self):
		name = self._save()
		api.mark_sent(name)

		doc = frappe.get_doc("Quotation", name)
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.status, "Open")
		with self.assertRaises(frappe.ValidationError):
			self._save(name=name)

	def test_rejected_records_the_reason_and_only_after_it_has_gone_out(self):
		name = self._save()
		with self.assertRaises(frappe.ValidationError):
			api.mark_rejected(name)

		api.mark_sent(name)
		api.mark_rejected(name, reason="Priced above budget")

		doc = frappe.get_doc("Quotation", name)
		self.assertEqual(doc.status, "Lost")
		self.assertEqual(doc.order_lost_reason, "Priced above budget")

	def test_accepted_confirms_a_sales_order_and_the_quotation_reads_ordered(self):
		name = self._save()
		api.mark_sent(name)

		order = api.mark_accepted(name)["sales_order"]

		self.assertEqual(frappe.db.get_value("Sales Order", order, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Quotation", name, "status"), "Ordered")

	def test_accepted_is_refused_twice_and_before_it_has_gone_out(self):
		name = self._save()
		with self.assertRaises(frappe.ValidationError):
			api.mark_accepted(name)

		api.mark_sent(name)
		api.mark_accepted(name)
		with self.assertRaises(frappe.ValidationError):
			api.mark_accepted(name)

	def test_a_copy_is_a_fresh_draft_carrying_the_same_lines(self):
		name = self._save()
		api.mark_sent(name)

		copy = frappe.get_doc("Quotation", api.copy_quotation(name)["name"])

		self.assertNotEqual(copy.name, name)
		self.assertEqual(copy.docstatus, 0)
		# copy_doc keeps no_copy fields unless told otherwise, and set_status skips a new doc —
		# so an unguarded copy of a sent quotation reads "Open" while sitting in draft.
		self.assertEqual(copy.status, "Draft")
		self.assertIsNone(copy.valid_till)
		self.assertEqual(str(copy.transaction_date), nowdate())
		self.assertEqual(copy.title, "UAT offer")
		self.assertEqual([line.item_name for line in copy.items], ["Site supervision"])

	def test_a_copy_of_a_rejected_quotation_does_not_inherit_the_rejection(self):
		name = self._submitted()
		api.mark_rejected(name, reason="Priced above budget")

		copy = frappe.get_doc("Quotation", api.copy_quotation(name)["name"])

		self.assertEqual(copy.status, "Draft")
		self.assertFalse(copy.order_lost_reason)
		self.assertFalse(copy.lost_reasons)

	def test_the_form_reads_back_what_it_saved(self):
		name = self._save(customer_type="Main Contractor", internal_note="Chase on Friday")

		loaded = api.get_quotation(name)

		self.assertEqual(loaded["party_name"], self.customer)
		self.assertEqual(loaded["customer_type"], "Main Contractor")
		self.assertEqual(loaded["internal_note"], "Chase on Friday")
		self.assertEqual([line["description"] for line in loaded["items"]], ["Site supervision"])

	# --- the summary cards -----------------------------------------------
	def test_win_rate_counts_won_against_won_plus_lost(self):
		won = frappe.db.count("Quotation", {"status": ("in", ("Ordered", "Partially Ordered"))})
		lost = frappe.db.count("Quotation", {"status": "Lost"})

		frappe.db.set_value("Quotation", self._submitted(), "status", "Ordered")
		frappe.db.set_value("Quotation", self._submitted(), "status", "Lost")

		self.assertEqual(api.get_summary()["win_rate"], round((won + 1) / (won + lost + 2) * 100))

	def test_a_quotation_nobody_has_answered_does_not_move_the_win_rate(self):
		before = api.get_summary()["win_rate"]
		frappe.db.set_value("Quotation", self._submitted(), "status", "Open")
		self.assertEqual(api.get_summary()["win_rate"], before)

	def test_a_quotation_with_no_validity_date_is_never_lapsed(self):
		before = api.get_summary()["lapsed_count"]
		name = self._save(valid_till=None)
		frappe.db.set_value("Quotation", name, "status", "Open")

		self.assertEqual(api.get_summary()["lapsed_count"], before)

		frappe.db.set_value("Quotation", name, "valid_till", add_days(nowdate(), -1))
		self.assertEqual(api.get_summary()["lapsed_count"], before + 1)
