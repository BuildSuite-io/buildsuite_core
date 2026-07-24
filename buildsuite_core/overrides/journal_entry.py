# <your_app>/overrides/journal_entry.py

from frappe.utils import flt

from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry


class CustomJournalEntry(JournalEntry):
	"""Journal Entry override.

	Only change vs upstream: carries the custom `employee` field from
	Journal Entry Account -> GL Entry via the args dict.

	on_submit() and make_gl_entries() are intentionally NOT overridden -
	Python resolves self.build_gl_map() to this class through the MRO,
	so inheriting them unchanged is both correct and upgrade-safe.
	"""

	def build_gl_map(self):
		gl_map = []
		for d in self.get("accounts"):
			if d.debit or d.credit or (self.voucher_type == "Exchange Gain Or Loss"):
				r = [d.user_remark, self.remark]
				r = [x for x in r if x]
				remarks = "\n".join(r)
				gl_map.append(
					self.get_gl_dict(
						{
							"account": d.account,
							"party_type": d.party_type,
							"due_date": self.due_date,
							"party": d.party,
							"against": d.against_account,
							"debit": flt(d.debit, d.precision("debit")),
							"credit": flt(d.credit, d.precision("credit")),
							"account_currency": d.account_currency,
							"debit_in_account_currency": flt(
								d.debit_in_account_currency, d.precision("debit_in_account_currency")
							),
							"credit_in_account_currency": flt(
								d.credit_in_account_currency, d.precision("credit_in_account_currency")
							),
							"against_voucher_type": d.reference_type,
							"against_voucher": d.reference_name,
							"remarks": remarks,
							"voucher_detail_no": d.reference_detail_no,
							"cost_center": d.cost_center,
							"project": d.project,
							"employee": d.employee,
							"finance_book": self.finance_book,
						},
						item=d,
					)
				)
		return gl_map