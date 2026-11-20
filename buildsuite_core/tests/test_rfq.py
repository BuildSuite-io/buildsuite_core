# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Request for Quotation, Supplier Quotation and their comparison (api/rfq), and the Purchase
Order raised from a quotation with its own order date (api/procurement_docs)."""

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api import procurement_docs as docs
from buildsuite_core.api import rfq as api
from buildsuite_core.permissions.setup import RFQ_DOCTYPES, RFQ_ROLE_PERMS
from buildsuite_core.tests.base import BuildSuiteTestCase


class RfqTestCase(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.project = self._make_project().name
		self.steel = self._item("Rebar")
		self.wire = self._item("Binding wire")
		self.jsw = self._supplier("JSW", "Deepak Shah", "deepak@jsw.example")
		self.shree = self._supplier("Shree", "Harish Patel", "harish@shree.example")
		self.tata = self._supplier("Tata")  # no contact on file

	def _supplier(self, label, contact=None, email=None):
		doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"UAT {label} {self._n}",
				"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name"),
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)
		if contact or email:
			from buildsuite_core.utils.party import upsert_primary_contact

			upsert_primary_contact("Supplier", doc.name, doc.supplier_name, contact, None, email)
		return doc.name

	def _item(self, label):
		return (
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": f"UAT-{label}-{self._n}",
					"item_name": f"UAT {label} {self._n}",
					"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
					"stock_uom": "Nos",
					"is_stock_item": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _lines(self):
		return [
			{"item_code": self.steel, "qty": 6800, "description": "Fe 500D, 12 m lengths"},
			{"item_code": self.wire, "qty": 84},
		]

	def _rfq(self, suppliers=None, submit=True, **kwargs):
		suppliers = suppliers or [self.jsw, self.shree, self.tata]
		rows = [api.get_supplier_contact(s) for s in suppliers]
		out = api.save_request_for_quotation(
			project=self.project,
			schedule_date=add_days(nowdate(), 14),
			closing_date=add_days(nowdate(), 5),
			subject="Request for Quotation: rebar and binding wire",
			message_for_supplier="Dear Sir / Madam,\n\nPlease send us your best quotation.",
			suppliers=frappe.as_json(rows),
			items=frappe.as_json(kwargs.pop("items", self._lines())),
			**kwargs,
		)
		if submit:
			out = api.submit_request_for_quotation(out["name"])
		return out

	def _quote(self, rfq, supplier, rates, submit=True, leads=(None, None), **kwargs):
		pre = api.get_rfq_for_sq(rfq)
		lines = pre["lines"]
		for line, rate, lead in zip(lines, rates, leads, strict=True):
			line["rate"] = rate
			line["lead_time_days"] = lead
		out = api.save_supplier_quotation(
			supplier=supplier,
			request_for_quotation=rfq,
			valid_till=kwargs.pop("valid_till", add_days(nowdate(), 30)),
			items=frappe.as_json(lines),
			**kwargs,
		)
		if submit:
			out = api.submit_supplier_quotation(out["name"])
		return out


class TestRequestForQuotation(RfqTestCase):
	def test_supplier_rows_take_the_masters_contact(self):
		rfq = self._rfq(submit=False)
		self.assertEqual(rfq["state"], "Draft")
		self.assertEqual(rfq["project"], self.project)
		self.assertEqual(rfq["company"], frappe.db.get_value("Project", self.project, "company"))
		rows = {s["supplier"]: s for s in rfq["suppliers"]}
		self.assertEqual(rows[self.jsw]["contact_person"], "Deepak Shah")
		self.assertEqual(rows[self.jsw]["email_id"], "deepak@jsw.example")
		self.assertEqual(rows[self.tata]["email_id"], "")
		self.assertFalse(rows[self.jsw]["differs_from_master"])
		self.assertEqual([it["qty"] for it in rfq["items"]], [6800, 84])
		self.assertEqual(rfq["items"][0]["description"], "Fe 500D, 12 m lengths")

	def test_needs_project_subject_supplier_and_item(self):
		ok = {
			"project": self.project,
			"subject": "S",
			"suppliers": frappe.as_json([{"supplier": self.jsw}]),
			"items": frappe.as_json(self._lines()),
		}
		for missing in ("project", "subject", "suppliers", "items"):
			with self.assertRaises(frappe.ValidationError, msg=missing):
				api.save_request_for_quotation(**{**ok, missing: None})
		bad = frappe.as_json([{"supplier": self.jsw, "email_id": "not-an-address"}])
		with self.assertRaises(frappe.ValidationError):
			api.save_request_for_quotation(**{**ok, "suppliers": bad})

	def test_from_material_request_carries_lines_and_links_back(self):
		wh = docs._default_warehouse(self.company, self.project)
		due = add_days(nowdate(), 7)
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": self.company,
				"project": self.project,
				"schedule_date": due,
				"items": [{"item_code": self.steel, "qty": 10, "schedule_date": due, "warehouse": wh}],
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			api.get_mr_for_rfq(mr.name)  # a draft request cannot be quoted for
		mr.submit()

		pre = api.get_mr_for_rfq(mr.name)
		self.assertEqual(pre["project"], self.project)
		self.assertEqual(len(pre["lines"]), 1)
		self.assertTrue(pre["subject"].startswith("Request for Quotation: "))

		rfq = self._rfq(items=pre["lines"])
		self.assertEqual(rfq["material_request"], mr.name)
		self.assertEqual(rfq["items"][0]["material_request_item"], mr.items[0].name)
		linked = docs.get_material_request(mr.name)["rfqs"]
		self.assertEqual(linked, [{"name": rfq["name"], "status": "Submitted"}])

	def test_submit_sends_nothing_and_only_a_draft_is_edited(self):
		before = frappe.db.count("Email Queue")
		rfq = self._rfq()
		self.assertEqual(rfq["state"], "Submitted")
		self.assertEqual(frappe.db.count("Email Queue"), before)
		self.assertFalse(any(s["email_sent"] for s in rfq["suppliers"]))
		self.assertFalse(frappe.db.exists("User", "deepak@jsw.example"))  # no portal user either
		with self.assertRaises(frappe.ValidationError):
			api.save_request_for_quotation(
				name=rfq["name"],
				project=self.project,
				subject="Changed",
				suppliers=frappe.as_json([{"supplier": self.jsw}]),
				items=frappe.as_json(self._lines()),
			)

	def test_contact_corrected_after_submit_and_saved_back(self):
		rfq = self._rfq()
		out = api.set_rfq_supplier_contact(
			rfq["name"], self.tata, contact_person="Meera Iyer", email_id="meera@tata.example"
		)
		row = next(s for s in out["suppliers"] if s["supplier"] == self.tata)
		self.assertEqual((row["contact_person"], row["email_id"]), ("Meera Iyer", "meera@tata.example"))
		self.assertTrue(row["differs_from_master"])
		with self.assertRaises(frappe.ValidationError):
			api.set_rfq_supplier_contact(rfq["name"], self.tata, email_id="nope")

		out = api.save_rfq_contact_to_supplier(rfq["name"], self.tata)
		row = next(s for s in out["suppliers"] if s["supplier"] == self.tata)
		self.assertFalse(row["differs_from_master"])
		self.assertEqual(api.get_supplier_contact(self.tata)["email_id"], "meera@tata.example")

	def test_email_is_per_supplier_and_skips_one_with_no_address(self):
		draft = self._rfq(submit=False)
		with self.assertRaises(frappe.ValidationError):
			api.send_rfq_emails(draft["name"])  # not before submit

		rfq = api.submit_request_for_quotation(draft["name"])
		mail = rfq["email"][self.jsw]
		self.assertEqual(mail["to"], "deepak@jsw.example")
		self.assertTrue(mail["body"].startswith("Dear Deepak Shah,"))
		self.assertNotIn("Sir / Madam", mail["body"])
		self.assertTrue(rfq["email"][self.tata]["body"].startswith("Dear Sir / Madam,"))

		frappe.flags.mute_emails = True
		before = frappe.db.count("Communication", {"reference_name": rfq["name"]})
		try:
			res = api.send_rfq_emails(rfq["name"], frappe.as_json([self.jsw, self.tata]))
		except frappe.ValidationError as e:
			if "outgoing email account" in str(e):
				self.skipTest("no outgoing Email Account on this site")
			raise
		self.assertEqual(len(res["sent"]), 1)
		self.assertEqual(len(res["skipped"]), 1)
		rows = {s["supplier"]: s for s in res["doc"]["suppliers"]}
		self.assertTrue(rows[self.jsw]["email_sent"] and rows[self.jsw]["email_sent_at"])
		self.assertFalse(rows[self.shree]["email_sent"])
		self.assertFalse(rows[self.tata]["email_sent"])
		self.assertEqual(frappe.db.count("Communication", {"reference_name": rfq["name"]}), before + 1)

	def test_print_is_addressed_to_the_supplier_picked(self):
		from buildsuite_core.print_formats import seed_print_formats

		seed_print_formats()
		rfq = self._rfq()
		first = api.get_rfq_print_html(rfq["name"])["html"]
		self.assertIn("REQUEST FOR QUOTATION", first)
		self.assertIn("Deepak Shah", first)
		other = api.get_rfq_print_html(rfq["name"], self.shree)["html"]
		self.assertIn("Harish Patel", other)
		self.assertNotIn("Deepak Shah", other)
		self.assertIn("Fe 500D, 12 m lengths", other)

	def test_cancel_waits_for_its_quotations_and_amend_starts_clean(self):
		rfq = self._rfq()
		sq = self._quote(rfq["name"], self.jsw, [66.5, 82])
		with self.assertRaises(frappe.ValidationError):
			api.cancel_request_for_quotation(rfq["name"])
		with self.assertRaises(frappe.ValidationError):
			api.delete_request_for_quotation(rfq["name"])  # submitted

		api.cancel_supplier_quotation(sq["name"])
		out = api.cancel_request_for_quotation(rfq["name"])
		self.assertEqual(out["state"], "Cancelled")
		with self.assertRaises(frappe.ValidationError):
			api.delete_request_for_quotation(rfq["name"])  # a quotation still refers to it

		amended = api.amend_request_for_quotation(rfq["name"])
		self.assertEqual(amended["state"], "Draft")
		self.assertEqual(amended["amended_from"], rfq["name"])
		self.assertTrue(all(s["quote_status"] == "Pending" for s in amended["suppliers"]))


class TestRfqListSummaries(RfqTestCase):
	def test_summaries_cover_only_the_requests_asked_for(self):
		"""The list asks for the rows on screen; only those are read and returned."""
		shown = self._rfq()
		self._rfq()  # another request, not on this page
		self._quote(shown["name"], self.jsw, [66.5, 82])

		out = api.rfq_list_summaries(frappe.as_json([shown["name"]]))
		self.assertEqual(list(out), [shown["name"]])
		row = out[shown["name"]]
		self.assertEqual((len(row["suppliers"]), row["received"], row["items"]), (3, 1, 2))

	def test_no_names_reads_nothing(self):
		self._rfq()
		self.assertEqual(api.rfq_list_summaries(), {})
		self.assertEqual(api.rfq_list_summaries("[]"), {})


class TestSupplierQuotation(RfqTestCase):
	def test_quotation_answers_the_request(self):
		rfq = self._rfq()
		sq = self._quote(rfq["name"], self.jsw, [66.5, 82], submit=False, leads=(5, 5))
		self.assertEqual(sq["state"], "Draft")
		self.assertEqual(sq["request_for_quotation"], rfq["name"])
		self.assertEqual(sq["project"], self.project)
		self.assertEqual(sq["total"], 6800 * 66.5 + 84 * 82)
		self.assertEqual(sq["items"][0]["lead_time_days"], 5)
		self.assertTrue(all(it["request_for_quotation_item"] for it in sq["items"]))
		row = lambda: next(  # noqa: E731
			s for s in api.get_request_for_quotation(rfq["name"])["suppliers"] if s["supplier"] == self.jsw
		)
		self.assertEqual(row()["quote_status"], "Pending")  # a draft is not an answer

		api.submit_supplier_quotation(sq["name"])
		self.assertEqual(row()["quote_status"], "Received")
		self.assertEqual(row()["quotation"]["name"], sq["name"])

		api.cancel_supplier_quotation(sq["name"])
		self.assertEqual(row()["quote_status"], "Pending")

	def test_part_quotation_still_counts_as_received(self):
		rfq = self._rfq()
		self._quote(rfq["name"], self.shree, [67.75, 0])
		row = next(
			s for s in api.get_request_for_quotation(rfq["name"])["suppliers"] if s["supplier"] == self.shree
		)
		self.assertEqual(row["quote_status"], "Received")

	def test_rules(self):
		rfq = self._rfq()
		with self.assertRaises(frappe.ValidationError):
			self._quote(rfq["name"], self._supplier("Stranger"), [1, 1])  # not asked
		blank = self._quote(rfq["name"], self.jsw, [0, 0], submit=False)
		with self.assertRaises(frappe.ValidationError):
			api.submit_supplier_quotation(blank["name"])  # no rate anywhere
		self._quote(rfq["name"], self.jsw, [66.5, 82])
		second = self._quote(rfq["name"], self.jsw, [60, 80], submit=False)
		with self.assertRaises(frappe.ValidationError):
			api.submit_supplier_quotation(second["name"])  # one live quotation per supplier
		draft = self._rfq(submit=False)
		with self.assertRaises(frappe.ValidationError):
			api.get_rfq_for_sq(draft["name"])

	def test_expired_is_read_off_the_date(self):
		rfq = self._rfq()
		sq = self._quote(rfq["name"], self.jsw, [66.5, 82])
		self.assertEqual(sq["status"], "Submitted")
		frappe.db.set_value("Supplier Quotation", sq["name"], "valid_till", add_days(nowdate(), -1))
		self.assertEqual(api.get_supplier_quotation(sq["name"])["status"], "Expired")

	def test_standalone_quotation_needs_no_request(self):
		out = api.save_supplier_quotation(
			supplier=self.jsw,
			project=self.project,
			items=frappe.as_json([{"item_code": self.steel, "qty": 10, "rate": 70}]),
		)
		self.assertIsNone(out["request_for_quotation"])
		self.assertEqual(out["total"], 700)


class TestSupplierQuotationComparison(RfqTestCase):
	def test_lowest_per_item_best_supplier_and_basket(self):
		rfq = self._rfq()
		# JSW is cheaper on the steel, Shree on the wire: the cheapest supplier is not the
		# cheapest basket. Tata has not answered.
		shree = self._quote(rfq["name"], self.shree, [67.75, 74], leads=(3, 2))
		jsw = self._quote(rfq["name"], self.jsw, [66.5, 82], leads=(5, 5))
		self._quote(rfq["name"], self.tata, [1, 1], submit=False)  # a draft stays out

		cmp = api.supplier_quotation_comparison(rfq["name"])
		# Columns follow the request's supplier order, not the order the quotations came in.
		self.assertEqual([t["quotation"] for t in cmp["totals"]], [jsw["name"], shree["name"]])
		steel, wire = cmp["rows"]
		self.assertEqual((steel["low"], steel["high"]), (66.5, 67.75))
		self.assertEqual((wire["low"], wire["high"]), (74, 82))
		self.assertEqual(wire["cells"][1]["lead_time_days"], 2)
		self.assertEqual([t["value"] for t in cmp["totals"]], [459088, 466916])
		self.assertEqual([t["lowest_on"] for t in cmp["totals"]], [1, 1])
		self.assertEqual(cmp["best_quotation"], jsw["name"])
		self.assertEqual(cmp["basket"], 6800 * 66.5 + 84 * 74)
		self.assertLess(cmp["basket"], cmp["totals"][0]["value"])
		self.assertEqual(len(cmp["pending"]), 1)

		picker = {r["name"]: r for r in api.comparison_requests()}
		self.assertEqual(picker[rfq["name"]]["quoted"], 2)

	def test_unquoted_item_reads_not_quoted_and_cannot_be_best(self):
		rfq = self._rfq()
		self._quote(rfq["name"], self.jsw, [66.5, 82])
		part = self._quote(rfq["name"], self.shree, [60, 0])
		cmp = api.supplier_quotation_comparison(rfq["name"])
		self.assertIsNone(cmp["rows"][1]["cells"][1])
		shree = cmp["totals"][1]
		self.assertFalse(shree["complete"])
		self.assertEqual(shree["quotation"], part["name"])
		self.assertNotEqual(cmp["best_quotation"], part["name"])  # cheaper, but not complete


class TestRfqPermissionPatch(RfqTestCase):
	def _rule(self, role, **values):
		name = frappe.db.get_value(
			"Custom DocPerm", {"parent": "Supplier Quotation", "role": role, "permlevel": 0}
		)
		if not name:
			name = (
				frappe.get_doc(
					{
						"doctype": "Custom DocPerm",
						"parent": "Supplier Quotation",
						"role": role,
						"permlevel": 0,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		flags = (
			"select",
			"read",
			"write",
			"create",
			"delete",
			"submit",
			"cancel",
			"amend",
			"print",
			"export",
			"report",
			"email",
		)
		frappe.db.set_value("Custom DocPerm", name, {f: values.get(f, 0) for f in flags})
		return name

	def test_a_pick_only_rule_is_raised_and_an_edited_rule_is_left_alone(self):
		from buildsuite_core.permissions.setup import grant_missing_rfq_permissions

		# The automatic rule a link brings: pick only (what existing sites had before this feature).
		picker = self._rule("BuildSuite Procurement Officer", select=1, print=1)
		# An admin's own edit: read only (no print, no write).
		edited = self._rule("BuildSuite Director", read=1)

		grant_missing_rfq_permissions()

		raised = frappe.db.get_value(
			"Custom DocPerm", picker, ["read", "write", "create", "submit", "select"], as_dict=True
		)
		self.assertEqual(dict(raised), {"read": 1, "write": 1, "create": 1, "submit": 1, "select": 1})
		kept = frappe.db.get_value("Custom DocPerm", edited, ["read", "write", "create"], as_dict=True)
		self.assertEqual(dict(kept), {"read": 1, "write": 0, "create": 0})

	def test_the_link_pick_grant_never_lowers_an_existing_read(self):
		"""The update grants `select` on every doctype the RFQ / quotation link to. A role that
		already reads one (an admin's grant, even without print) keeps that read; a role that had
		no rule at all gets pick-only (select, no read)."""
		from buildsuite_core.permissions.setup import grant_missing_rfq_permissions

		def rule(role):
			return frappe.db.get_value(
				"Custom DocPerm",
				{"parent": "Incoterm", "role": role, "permlevel": 0},
				["select", "read"],
				as_dict=True,
			)

		reader = frappe.db.get_value(
			"Custom DocPerm", {"parent": "Incoterm", "role": "BuildSuite Procurement Officer", "permlevel": 0}
		)
		if not reader:
			self.skipTest("Incoterm has no customised rules on this site")
		frappe.db.set_value("Custom DocPerm", reader, {"select": 0, "read": 1, "print": 0})
		frappe.db.delete("Custom DocPerm", {"parent": "Incoterm", "role": "BuildSuite Director"})

		grant_missing_rfq_permissions()

		self.assertEqual(dict(rule("BuildSuite Procurement Officer")), {"select": 1, "read": 1})
		self.assertEqual(dict(rule("BuildSuite Director")), {"select": 1, "read": 0})


class TestQuotationsRespectRecordAccess(RfqTestCase):
	"""A user restricted to some quotations (a User Permission on Supplier for quotations) sees only those on
	the request page and in the comparison, and only those are counted in the request picker."""

	def _restricted_user(self, supplier):
		email = f"rfq-restricted-{self._n}-{frappe.generate_hash(length=6)}@example.com"
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Restricted", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		user.add_roles("BuildSuite Procurement Officer")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": email,
				"allow": "Supplier",
				"for_value": supplier,
				# Only quotations are restricted ("this buyer handles JSW's quotes"); a request lists
				# every supplier, so a restriction on all doctypes would hide the request itself.
				"apply_to_all_doctypes": 0,
				"applicable_for": "Supplier Quotation",
			}
		).insert(ignore_permissions=True)
		return email

	def test_only_the_quotations_the_user_may_read(self):
		rfq = self._rfq()
		mine = self._quote(rfq["name"], self.jsw, [66.5, 82])
		self._quote(rfq["name"], self.shree, [67.75, 80])

		frappe.set_user(self._restricted_user(self.jsw))
		self.addCleanup(frappe.set_user, "Administrator")

		page = api.get_request_for_quotation(rfq["name"])
		self.assertEqual([q["name"] for q in page["quotations"]], [mine["name"]])

		cmp = api.supplier_quotation_comparison(rfq["name"])
		self.assertEqual([t["quotation"] for t in cmp["totals"]], [mine["name"]])

		picker = {r["name"]: r for r in api.comparison_requests()}
		self.assertEqual(picker[rfq["name"]]["quoted"], 1)


class TestPurchaseOrderFromQuotation(RfqTestCase):
	def _order(self, pre, lines=None, submit=False):
		po = docs.save_purchase_order(
			supplier=pre["supplier"],
			project=pre["project"],
			schedule_date=pre["schedule_date"],
			supplier_quotation=pre["supplier_quotation"],
			items=frappe.as_json(lines if lines is not None else pre["lines"]),
		)
		if submit:
			docs.submit_purchase_order(po["name"])
		return po

	def test_order_takes_rates_and_links_and_leaves_nothing_to_order(self):
		rfq = self._rfq()
		sq = self._quote(rfq["name"], self.shree, [67.75, 0])
		pre = api.get_sq_for_po(sq["name"])
		self.assertEqual(pre["supplier"], self.shree)
		self.assertEqual(len(pre["lines"]), 1)  # only what the supplier priced
		self.assertEqual(pre["lines"][0]["rate"], 67.75)
		self.assertEqual(pre["schedule_date"], rfq["schedule_date"])
		self.assertTrue(api.get_supplier_quotation(sq["name"])["to_order"])

		po = self._order(pre)
		self.assertEqual(po["supplier_quotation"], sq["name"])
		self.assertEqual(
			po["items"][0]["supplier_quotation_item"], pre["lines"][0]["supplier_quotation_item"]
		)
		got = api.get_supplier_quotation(sq["name"])
		self.assertEqual(got["purchase_orders"][0]["name"], po["name"])
		with self.assertRaises(frappe.ValidationError):
			api.cancel_supplier_quotation(sq["name"])  # a live order was raised from it

		# Even the draft order counts: the quotation can't be ordered from a second time.
		self.assertEqual(api.get_sq_for_po(sq["name"])["lines"], [])
		self.assertFalse(got["to_order"])
		self.assertEqual(got["items"][0]["ordered_qty"], 6800)
		# ERPNext's own status: Supplier Quotation has no Ordered state.
		self.assertEqual(got["status"], "Submitted")

	def test_a_part_order_leaves_the_rest_to_order(self):
		rfq = self._rfq()
		sq = self._quote(rfq["name"], self.jsw, [66.5, 82])
		pre = api.get_sq_for_po(sq["name"])
		first = [dict(pre["lines"][0], qty=2000), pre["lines"][1]]
		self._order(pre, first, submit=True)

		again = api.get_sq_for_po(sq["name"])
		self.assertEqual([(ln["item_code"], ln["qty"]) for ln in again["lines"]], [(self.steel, 4800)])
		self.assertTrue(api.get_supplier_quotation(sq["name"])["to_order"])

	def test_a_cancelled_order_frees_its_quantity_again(self):
		rfq = self._rfq()
		sq = self._quote(rfq["name"], self.shree, [67.75, 0])
		po = self._order(api.get_sq_for_po(sq["name"]), submit=True)
		self.assertEqual(api.get_sq_for_po(sq["name"])["lines"], [])

		docs.cancel_purchase_order(po["name"])
		self.assertEqual([ln["qty"] for ln in api.get_sq_for_po(sq["name"])["lines"]], [6800])

	def test_order_date_is_the_users_but_never_in_the_future(self):
		line = frappe.as_json([{"item_code": self.steel, "qty": 5, "rate": 10}])
		earlier = add_days(nowdate(), -3)
		po = docs.save_purchase_order(
			supplier=self.jsw, project=self.project, transaction_date=earlier, items=line
		)
		self.assertEqual(po["transaction_date"], earlier)
		po = docs.save_purchase_order(name=po["name"], supplier=self.jsw, project=self.project, items=line)
		self.assertEqual(po["transaction_date"], earlier)  # an edit that names no date keeps it
		with self.assertRaises(frappe.ValidationError):
			docs.save_purchase_order(
				supplier=self.jsw, project=self.project, transaction_date=add_days(nowdate(), 1), items=line
			)


class TestRfqPermissions(RfqTestCase):
	def test_matrix_is_admin_director_and_procurement_only(self):
		self.assertEqual(
			set(RFQ_ROLE_PERMS),
			{"BuildSuite Administrator", "BuildSuite Director", "BuildSuite Procurement Officer"},
		)
		for perms in RFQ_ROLE_PERMS.values():
			for ptype in ("read", "write", "create", "delete", "submit", "cancel", "amend", "email"):
				self.assertEqual(perms.get(ptype), 1, ptype)

	def test_seeded_rules_keep_the_other_personas_out(self):
		from buildsuite_core.permissions.setup import BUILDSUITE_ROLES, setup_purchase_stock_permissions

		setup_purchase_stock_permissions()
		for doctype in RFQ_DOCTYPES:
			readers = set(
				frappe.get_all(
					"Custom DocPerm",
					filters={"parent": doctype, "permlevel": 0, "read": 1, "role": ["in", BUILDSUITE_ROLES]},
					pluck="role",
				)
			)
			self.assertEqual(readers, set(RFQ_ROLE_PERMS), doctype)

	def test_comparison_report_is_anchored_and_tiled(self):
		from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import _SEED
		from buildsuite_core.report_access import ROUTE_TO_REPORT

		route = "/procurement/supplier-quotation-comparison"
		self.assertEqual(ROUTE_TO_REPORT[route], "BuildSuite Supplier Quotation Comparison")
		self.assertIn(route, [t.get("route") for t in _SEED["procurement"]])
