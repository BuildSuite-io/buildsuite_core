// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

const CHILD_TABLE = "expense_entry_table";
const INHERITED_FIELDS = [
	"payment_account",
	"payment_account_name",
	"employee",
	"project",
	"cost_center",
];

frappe.ui.form.on("Expense Entry", {
	setup(frm) {
		set_queries(frm);
	},

	onload(frm) {
		if (frm.is_new()) {
			if (!frm.doc.company) {
				frm.set_value("company", frappe.defaults.get_user_default("Company"));
			}
			if (!frm.doc.date) {
				frm.set_value("date", frappe.datetime.get_today());
			}
		}
		set_default_cost_center(frm);
	},

	refresh(frm) {
		set_default_cost_center(frm);
		update_child_readonly(frm);
		add_ledger_button(frm);
	},

	company(frm) {
		frm.set_value("cost_center", null);
		frm.set_value("payment_account", null);
		set_default_cost_center(frm);
	},

	payment_account: propagate_to_child("payment_account"),
	payment_account_name: propagate_to_child("payment_account_name"),
	employee: propagate_to_child("employee"),
	project: propagate_to_child("project"),
	cost_center: propagate_to_child("cost_center"),
});

frappe.ui.form.on("Expense Entry Table", {
	[`${CHILD_TABLE}_add`](frm, cdt, cdn) {
		INHERITED_FIELDS.forEach((field) => {
			if (frm.doc[field]) {
				frappe.model.set_value(cdt, cdn, field, frm.doc[field]);
			}
		});
	},
});


function set_default_payment_account(frm) {
	if (frm.doc.docstatus !== 0 || frm.doc.payment_account || !frm.doc.company) return;

	frappe.call({
		method: "buildsuite_core.buildsuite_core.doctype.expense_entry.expense_entry.get_default_payment_account",
		args: { company: frm.doc.company },
		callback: (r) => {
			if (r.message && !frm.doc.payment_account) {
				frm.set_value("payment_account", r.message);
			}
		},
	});
}
// ---------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------

function set_queries(frm) {
	const company_only = () => ({ filters: { company: frm.doc.company } });

	frm.set_query("employee", () => ({
		filters: { company: frm.doc.company, status: "Active" },
	}));

	frm.set_query("cost_center", () => ({
		filters: { company: frm.doc.company, is_group: 0 },
	}));

	frm.set_query("project", company_only);

	const payment_account_query = () => ({
		filters: {
			account_type: ["in", ["Bank", "Cash"]],
			is_group: 0,
			company: frm.doc.company,
		},
	});

	frm.set_query("payment_account", payment_account_query);
	frm.set_query("payment_account", CHILD_TABLE, payment_account_query);

	frm.set_query("expense_account", CHILD_TABLE, () => ({
		filters: { is_group: 0, root_type: "Expense", company: frm.doc.company },
	}));

	frm.set_query("cost_center", CHILD_TABLE, () => ({
		filters: { company: frm.doc.company, is_group: 0 },
	}));

	frm.set_query("project", CHILD_TABLE, company_only);
}

// ---------------------------------------------------------------------
// Parent -> child propagation
// ---------------------------------------------------------------------

function propagate_to_child(field) {
	return function (frm) {
		const rows = frm.doc[CHILD_TABLE] || [];
		const value = frm.doc[field];

		if (value) {
			rows.forEach((row) => {
				if (row[field] !== value) {
					frappe.model.set_value(row.doctype, row.name, field, value);
				}
			});
		}

		update_child_readonly(frm);
	};
}

function update_child_readonly(frm) {
	const grid = frm.fields_dict[CHILD_TABLE]?.grid;
	if (!grid) return;

	INHERITED_FIELDS.forEach((field) => {
		grid.update_docfield_property(field, "read_only", frm.doc[field] ? 1 : 0);
	});

	grid.refresh();
}

// ---------------------------------------------------------------------
// Buttons
// ---------------------------------------------------------------------

function add_ledger_button(frm) {
	if (!frm.doc.journal_entry) return;

	frm.add_custom_button(__("View Ledger"), () => {
		frappe.set_route("query-report", "General Ledger", {
			company: frm.doc.company,
			voucher_no: frm.doc.journal_entry,
			from_date: frm.doc.date,
			to_date: frm.doc.date,
			group_by: "Group by Voucher (Consolidated)",
		});
	});

	frm.add_custom_button(__("Journal Entry"), () => {
		frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
	}, __("View"));
}
function set_default_cost_center(frm) {
	if (frm.doc.docstatus !== 0 || frm.doc.cost_center || !frm.doc.company) return;

	frappe.db.get_value("Company", frm.doc.company, "cost_center").then((r) => {
		const from_company = r?.message?.cost_center;
		if (from_company) return apply(from_company);

		const from_user = frappe.defaults.get_user_default("Cost Center");
		if (from_user) return apply(from_user);

		// Last resort: the company's only leaf cost center
		frappe.db
			.get_list("Cost Center", {
				filters: { company: frm.doc.company, is_group: 0 },
				fields: ["name"],
				limit: 2,
			})
			.then((rows) => {
				if (rows.length === 1) apply(rows[0].name);
			});
	});

	function apply(value) {
		// Re-check: the user may have picked one while the request was in flight
		if (!frm.doc.cost_center) frm.set_value("cost_center", value);
	}
}