import frappe

from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry
from erpnext.accounts.utils import (
	cancel_exchange_gain_loss_journal,
	get_account_currency,
	get_balance_on,
	get_stock_accounts,
	get_stock_and_account_balance,
)

class CustomJournalEntry(JournalEntry):
    def on_submit(self):
        self.validate_cheque_info()
        self.check_credit_limit()
        self.make_gl_entries()
        self.update_advance_paid()
        self.update_asset_value()
        self.update_inter_company_jv()
        self.update_invoice_discounting()

    def make_gl_entries(self, cancel=0, adv_adj=0):
        from erpnext.accounts.general_ledger import make_gl_entries
        merge_entries = frappe.db.get_single_value("Accounts Settings", "merge_similar_account_heads")
        gl_map = self.build_gl_map()
        if self.voucher_type in ("Deferred Revenue", "Deferred Expense"):
            update_outstanding = "No"
        else:
            update_outstanding = "Yes"
        if gl_map:
            make_gl_entries(
                gl_map,
                cancel=cancel,
                adv_adj=adv_adj,
                merge_entries=merge_entries,
                update_outstanding=update_outstanding,
            )
            if cancel:
                cancel_exchange_gain_loss_journal(frappe._dict(doctype=self.doctype, name=self.name))


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
                            "employee":d.employee,
                            "finance_book": self.finance_book,
                        },
                        item=d,
                    )
                )
        return gl_map