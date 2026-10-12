# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Estimation › Quotations — drafts on ERPNext's own Quotation doctype.

There is no quotation endpoint: the Vue views create, read and edit the doctype straight through
the data adapter. So what is worth testing here is the shape the app relies on — that a line
built the way the form builds it saves, and that the custom fields carry what they are for.
Submitting, accepting and rejecting come later, with their own tests.
"""

import frappe
from frappe.utils import flt

from buildsuite_core.api.invoice import ensure_invoice_item
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestQuotation(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.customer = self._make_customer().name
		self.item = ensure_invoice_item()

	def _save(self, **overrides):
		"""A quotation in exactly the shape NewQuotationView.vue posts."""
		payload = {
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"party_name": self.customer,
			"title": "UAT offer",
			"items": [
				{
					"item_code": self.item,
					"item_name": "Site supervision",
					"description": "Site supervision",
					"uom": "Nos",
					"qty": 2,
					"price_list_rate": 500,
					"margin_type": "Percentage",
					"margin_rate_or_amount": 0,
					"source": "Manual",
				}
			],
		}
		payload.update(overrides)
		doc = frappe.get_doc(payload)
		doc.insert()
		return doc

	def test_a_line_typed_in_the_form_saves_as_a_draft(self):
		doc = self._save()

		self.assertEqual(doc.docstatus, 0)
		self.assertEqual(doc.party_name, self.customer)
		# ERPNext fills these itself — the form sends none of them.
		self.assertTrue(doc.company)
		self.assertTrue(doc.currency)
		self.assertEqual(flt(doc.items[0].amount), 1000)

	def test_free_text_hangs_off_the_shared_service_item(self):
		"""A quotation line is a scope of work, not stock, so every line points at one generic
		Item and the typed text rides in item_name / description."""
		line = self._save().items[0]

		self.assertEqual(line.item_code, "Professional Services")
		self.assertEqual(line.item_name, "Site supervision")

	def test_a_line_keeps_its_own_code_and_the_assembly_it_came_from(self):
		"""Two fields, not one: editing the code must not lose the trail back to the catalogue."""
		doc = self._save(
			items=[
				{
					"item_code": self.item,
					"item_name": "Plaster",
					"description": "Plaster",
					"uom": "Nos",
					"qty": 1,
					"rate": 10,
					"source": "Assembly",
					"code": "MY-01",
					"source_ref": "ASM-PLASTER",
				}
			]
		)

		line = doc.items[0]
		self.assertEqual(line.source, "Assembly")
		self.assertEqual(line.code, "MY-01")
		self.assertEqual(line.source_ref, "ASM-PLASTER")

	def test_source_ref_is_read_only_so_the_browser_cannot_set_it_by_hand(self):
		"""It is the catalogue's word, not the estimator's — the picker fills it on the server
		side of the link, and the form leaves it alone."""
		meta = frappe.get_meta("Quotation Item")
		self.assertTrue(meta.get_field("source_ref").read_only)
		self.assertFalse(meta.get_field("code").read_only)

	def test_the_customer_type_field_is_there_to_filter_the_list_on(self):
		doc = self._save(customer_type="Main Contractor", internal_note="Chase on Friday")

		self.assertEqual(doc.customer_type, "Main Contractor")
		self.assertEqual(doc.internal_note, "Chase on Friday")

	# --- margin ------------------------------------------------------------
	def _line(self, margin, cost=100, qty=2):
		return {
			"item_code": self.item,
			"item_name": "Site supervision",
			"description": "Site supervision",
			"uom": "Nos",
			"qty": qty,
			"price_list_rate": cost,
			"margin_type": "Percentage",
			"margin_rate_or_amount": margin,
		}

	def test_the_margin_is_added_to_every_line_not_lumped_on_the_total(self):
		"""A customer expects the rate they are quoted to be the rate they pay, so the rows have
		to sum to the total under them. ERPNext derives rate from price_list_rate + margin."""
		doc = self._save(items=[self._line(10)])

		line = doc.items[0]
		self.assertEqual(flt(line.price_list_rate), 100)
		self.assertEqual(line.margin_type, "Percentage")
		self.assertEqual(flt(line.rate), 110)
		self.assertEqual(flt(line.amount), 220)
		self.assertEqual(flt(doc.net_total), 220)

	def test_changing_the_margin_reprices_on_every_save_not_only_the_first(self):
		"""taxes_and_totals.py:1162 rewrites margin_type to "Amount" whenever it finds a rate
		above the cost, which after one save it always is. Replacing the whole items table —
		what the form does — means rows arrive with no stale rate, so the percentage survives.
		This is the regression an earlier attempt shipped."""
		doc = self._save(items=[self._line(10)])

		doc.set("items", [])
		doc.append("items", self._line(20))
		doc.save()
		self.assertEqual(flt(doc.items[0].rate), 120)
		self.assertEqual(flt(doc.net_total), 240)
		self.assertEqual(doc.items[0].margin_type, "Percentage")

		doc.set("items", [])
		doc.append("items", self._line(0))
		doc.save()
		self.assertEqual(flt(doc.items[0].rate), 100)
		self.assertEqual(flt(doc.net_total), 200)

	def test_an_old_line_survives_being_opened_and_saved_again(self):
		"""Quotations saved before margin existed carry a rate and no cost. The form reads the
		cost, so without a fallback it loads zero and the next save wipes the line. Testing the
		insert alone missed this — it is the round trip that breaks."""
		doc = self._save(
			items=[
				{
					"item_code": self.item,
					"item_name": "Old line",
					"description": "Old line",
					"uom": "Nos",
					"qty": 1,
					"rate": 500,
				}
			]
		)
		self.assertEqual(flt(doc.items[0].price_list_rate), 0)

		# What the form posts back: the cost it read, falling back to the rate.
		line = doc.items[0]
		cost = flt(line.price_list_rate) or flt(line.rate)
		doc.set("items", [])
		doc.append("items", dict(self._line(0, cost=cost, qty=1), item_name="Old line",
		                         description="Old line"))
		doc.save()

		self.assertEqual(flt(doc.items[0].rate), 500)
		self.assertEqual(flt(doc.net_total), 500)
