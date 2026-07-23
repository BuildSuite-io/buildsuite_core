// Project Finance — self-contained CLIENT-SIDE MOCK store. Everything in the Project Finance
// workspace runs on this dummy data (session-scoped, resets on reload) — exactly like the demo —
// EXCEPT Petty Cash, which is live (see pettyCashApi / FinancePettyCashPanel). Holds the seed
// arrays + name resolvers + derived getters + mutation actions the panels/reports use.

import { defineStore } from "pinia";

let seq = 1000;
const uid = (p) => `${p}-${++seq}`;
const today = () => new Date().toISOString().slice(0, 10);
const daysBetween = (a, b) => Math.round((new Date(a) - new Date(b)) / 86400000);

export const useFinanceMock = defineStore("financeMock", {
	state: () => ({
		companies: [
			{ id: "ACME-COM", name: "Acme Construction Co", shortName: "Acme", color: "bg-brand-500" },
			{ id: "ACME-RES", name: "Acme Residential", shortName: "Acme Res", color: "bg-info-500" },
		],
		users: [
			{ id: "USR-001", name: "Anita Rao" },
			{ id: "USR-005", name: "Kiran Mehta" },
			{ id: "USR-008", name: "Suresh Nair" },
		],
		projects: [
			{ id: "PROJ-2026-001-A", name: "Block A — Office Tower", code: "BTP-P2-A", company: "ACME-COM" },
			{ id: "PROJ-2026-002", name: "Riverside Residency", code: "RR-01", company: "ACME-RES" },
		],
		financeAccounts: [
			{ id: "ACC-BANK-01", name: "HDFC Current A/c", type: "Bank", account_no: "50200011223344", opening_balance: 5000000, company: "ACME-COM" },
			{ id: "ACC-CASH-01", name: "Cash in Hand", type: "Cash", account_no: "", opening_balance: 200000, company: "ACME-COM" },
		],
		customers: [
			{ id: "CUST-001", name: "ABC Constructions", type: "Company", contactPerson: "Rajesh Kumar", phone: "+91 98501 23401", email: "rajesh@abccons.example", gstin: "29AABCC1001A1Z5", company: "ACME-COM" },
			{ id: "CUST-002", name: "Sunrise Developers", type: "Partnership", contactPerson: "Meera Iyer", phone: "+91 98450 55220", email: "meera@sunrise.example", gstin: "29AAFCS2002B1Z4", company: "ACME-RES" },
		],
		suppliers: [
			{ id: "SUP-001", name: "UltraTech Cement Ltd", type: "Material", contactPerson: "Naveen Rao", phone: "+91 98450 71001", email: "naveen.rao@ultratech.example", gstin: "29AABCU1001A1Z5", company: "ACME-COM" },
			{ id: "SUP-002", name: "Tata Steel", type: "Material", contactPerson: "Deepak Shah", phone: "+91 90080 22110", email: "deepak@tatasteel.example", gstin: "27AAACT2727Q1ZW", company: "ACME-COM" },
		],
		subcontractors: [
			{ id: "SC-001", name: "Sterling Flooring Co", trade: "Flooring", contactPerson: "Ali Khan", phone: "+91 99001 22334", gstin: "29AASFS3003C1Z3", status: "Active" },
		],
		subcontractorBills: [
			{ id: "SB-2026-0001", supplier: "SC-001", project: "PROJ-2026-001-A", date: "2026-06-05", gross: 204000, retention: 10200, total: 193800, company: "ACME-COM", paymentEntries: [] },
		],
		invoices: [
			{ id: "INV-2026-0001", workflow_state: "Submitted", customer: "CUST-001", project: "PROJ-2026-001-A", date: "2026-06-01", due_date: "2026-07-01", gst_rate: 18, gross: 2500000, tax: 450000, total: 2950000, company: "ACME-COM", lines: [{ id: "INL-1", description: "Block A — RA-3 milestone", amount: 2500000 }], receipts: [{ id: "RCPT-1", date: "2026-07-05", amount: 1000000, account: "ACC-BANK-01" }] },
			{ id: "INV-2026-0002", workflow_state: "Submitted", customer: "CUST-002", project: "PROJ-2026-002", date: "2026-05-20", due_date: "2026-06-19", gst_rate: 18, gross: 1200000, tax: 216000, total: 1416000, company: "ACME-RES", lines: [{ id: "INL-2", description: "Foundation works", amount: 1200000 }], receipts: [] },
		],
		bills: [
			{ id: "BILL-2026-0001", supplier: "SUP-001", project: "PROJ-2026-001-A", date: "2026-06-10", due_date: "2026-07-10", gst_rate: 18, gross: 450000, tax: 81000, total: 531000, company: "ACME-COM", lines: [{ id: "BLL-1", description: "OPC 53 cement — 900 bags", amount: 450000 }], payments: [{ id: "PMT-1", date: "2026-07-05", amount: 200000, account: "ACC-BANK-01" }] },
			{ id: "BILL-2026-0002", supplier: "SUP-002", project: "PROJ-2026-001-A", date: "2026-06-18", due_date: "2026-07-18", gst_rate: 18, gross: 780000, tax: 140400, total: 920400, company: "ACME-COM", lines: [{ id: "BLL-2", description: "TMT bars Fe550 — 40 T", amount: 780000 }], payments: [] },
		],
		expenses: [
			{ id: "EXP-2026-0001", date: "2026-06-22", description: "Safety helmets, gloves, jackets", amount: 6400, project: "PROJ-2026-001-A", expense_account: "Site Safety Expenses", cost_type: "Overhead", paid_from: "ACC-CASH-01", holder: "USR-005", status: "Submitted", reimbursed: false, company: "ACME-COM" },
			{ id: "EXP-2026-0002", date: "2026-07-02", description: "Diesel for concrete pump", amount: 8200, project: "PROJ-2026-001-A", expense_account: "Fuel & Lubricants", cost_type: "Plant & Machinery", paid_from: "ACC-CASH-01", holder: "USR-005", status: "Draft", reimbursed: false, company: "ACME-COM" },
		],
		customerAdvances: [
			{ id: "CADV-2026-0001", customer: "CUST-002", date: "2026-06-15", amount: 500000, account: "ACC-BANK-01", allocated: 0, company: "ACME-RES" },
		],
		supplierAdvances: [
			{ id: "SADV-2026-0001", supplier: "SUP-001", date: "2026-06-05", amount: 150000, account: "ACC-BANK-01", allocated: 0, company: "ACME-COM" },
		],
		paymentEntries: [],
	}),

	getters: {
		// --- name resolvers ---
		projectName: (s) => (id) => s.projects.find((p) => p.id === id)?.name || id || "—",
		userName: (s) => (id) => s.users.find((u) => u.id === id)?.name || id || "—",
		companyById: (s) => (id) => s.companies.find((c) => c.id === id) || null,
		accountById: (s) => (id) => s.financeAccounts.find((a) => a.id === id) || null,
		customerById: (s) => (id) => s.customers.find((c) => c.id === id) || null,
		supplierById: (s) => (id) => s.suppliers.find((c) => c.id === id) || null,
		partyName() {
			return (kind, id) => (kind === "customer" ? this.customerById(id)?.name : this.supplierById(id)?.name) || id;
		},

		// --- invoices / receivables ---
		postedInvoices: (s) => s.invoices.filter((i) => i.workflow_state === "Submitted"),
		invoiceOutstanding: () => (inv) => (inv.total || 0) - (inv.receipts || []).reduce((a, r) => a + (r.amount || 0), 0),
		openInvoices() {
			return this.postedInvoices.filter((i) => this.invoiceOutstanding(i) > 0.5);
		},
		totalReceivable() {
			return this.openInvoices.reduce((a, i) => a + this.invoiceOutstanding(i), 0);
		},

		// --- bills / payables ---
		billOutstanding: () => (b) => (b.total || 0) - (b.payments || []).reduce((a, p) => a + (p.amount || 0), 0),
		scBillOutstanding: () => (b) => (b.total || 0) - (b.paymentEntries || []).reduce((a, p) => a + (p.amount || 0), 0),
		unifiedPayables() {
			const regular = this.bills.map((b) => ({ kind: "regular", ...b, outstanding: this.billOutstanding(b), retention: 0 }));
			const sub = this.subcontractorBills.map((b) => ({ kind: "subcontractor", ...b, outstanding: this.scBillOutstanding(b) }));
			return [...regular, ...sub];
		},
		totalPayable() {
			return this.unifiedPayables.reduce((a, b) => a + (b.outstanding || 0), 0);
		},
		retentionHeld: (s) => s.subcontractorBills.reduce((a, b) => a + (b.retention || 0), 0),

		// --- accounts / cash ---
		accountBalance() {
			return (accId) => {
				const acc = this.accountById(accId);
				if (!acc) return 0;
				let bal = acc.opening_balance || 0;
				this.invoices.forEach((i) => (i.receipts || []).forEach((r) => r.account === accId && (bal += r.amount)));
				this.customerAdvances.forEach((a) => a.account === accId && (bal += a.amount));
				this.bills.forEach((b) => (b.payments || []).forEach((p) => p.account === accId && (bal -= p.amount)));
				this.supplierAdvances.forEach((a) => a.account === accId && (bal -= a.amount));
				return bal;
			};
		},
		sortedFinanceAccounts: (s) => [...s.financeAccounts].sort((a, b) => a.name.localeCompare(b.name)),
		totalCashBank() {
			return this.financeAccounts.filter((a) => a.type !== "Petty Cash").reduce((a, acc) => a + this.accountBalance(acc.id), 0);
		},

		// --- expenses ---
		verifiedExpenses: (s) => s.expenses.filter((e) => e.status === "Submitted"),
		expensesToVerify: (s) => s.expenses.filter((e) => e.status === "Draft"),

		// --- aging ---
		agingBucket: () => (dueDate) => {
			if (!dueDate) return "Not due";
			const d = daysBetween(today(), dueDate);
			if (d <= 0) return "Not due";
			if (d <= 30) return "0-30d";
			if (d <= 60) return "31-60d";
			return "60+d";
		},

		// --- unified payment register ---
		allPayments() {
			const out = [];
			this.invoices.forEach((i) => (i.receipts || []).forEach((r) => out.push({ id: r.id, date: r.date, type: "Invoice receipt", dir: "in", party: this.customerById(i.customer)?.name, account: r.account, amount: r.amount, ref: i.id })));
			this.customerAdvances.forEach((a) => out.push({ id: a.id, date: a.date, type: "Customer advance", dir: "in", party: this.customerById(a.customer)?.name, account: a.account, amount: a.amount, ref: a.id }));
			this.bills.forEach((b) => (b.payments || []).forEach((p) => out.push({ id: p.id, date: p.date, type: "Bill payment", dir: "out", party: this.supplierById(b.supplier)?.name, account: p.account, amount: p.amount, ref: b.id })));
			this.supplierAdvances.forEach((a) => out.push({ id: a.id, date: a.date, type: "Supplier advance", dir: "out", party: this.supplierById(a.supplier)?.name, account: a.account, amount: a.amount, ref: a.id }));
			return out.sort((a, b) => new Date(b.date) - new Date(a.date));
		},
	},

	actions: {
		addCustomer(d) { const r = { id: uid("CUST"), allocated: 0, ...d }; this.customers.push(r); return r; },
		addSupplier(d) { const r = { id: uid("SUP"), ...d }; this.suppliers.push(r); return r; },
		addInvoice(d) {
			const gross = (d.lines || []).reduce((a, l) => a + (Number(l.amount) || 0), 0);
			const tax = Math.round((gross * (Number(d.gst_rate) || 0)) / 100);
			const r = { id: uid("INV"), workflow_state: "Submitted", gross, tax, total: gross + tax, receipts: [], ...d };
			this.invoices.unshift(r);
			return r;
		},
		addInvoiceReceipt(id, amount, account) {
			const inv = this.invoices.find((i) => i.id === id);
			if (inv) inv.receipts.push({ id: uid("RCPT"), date: today(), amount: Number(amount), account });
		},
		addBill(d) {
			const gross = (d.lines || []).reduce((a, l) => a + (Number(l.amount) || 0), 0);
			const tax = Math.round((gross * (Number(d.gst_rate) || 0)) / 100);
			const r = { id: uid("BILL"), gross, tax, total: gross + tax, payments: [], ...d };
			this.bills.unshift(r);
			return r;
		},
		addBillPayment(id, amount, account) {
			const b = this.bills.find((x) => x.id === id);
			if (b) b.payments.push({ id: uid("PMT"), date: today(), amount: Number(amount), account });
		},
		addCustomerAdvance(d) { const r = { id: uid("CADV"), date: today(), allocated: 0, ...d }; this.customerAdvances.push(r); return r; },
		addSupplierAdvance(d) { const r = { id: uid("SADV"), date: today(), allocated: 0, ...d }; this.supplierAdvances.push(r); return r; },
		addExpense(d) { const r = { id: uid("EXP"), date: today(), status: "Draft", reimbursed: false, ...d }; this.expenses.unshift(r); return r; },
		submitExpense(id) { const e = this.expenses.find((x) => x.id === id); if (e) e.status = "Submitted"; },
		cancelExpense(id) { const e = this.expenses.find((x) => x.id === id); if (e) e.status = "Cancelled"; },
	},
});
