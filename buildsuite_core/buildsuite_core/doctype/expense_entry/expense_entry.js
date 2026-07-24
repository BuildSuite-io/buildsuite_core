// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expense Entry", {
	setup: function (frm) {
        set_expense_queries(frm);
    },
    before_save: function (frm) {
        if (frm.is_new()) {
            frm.set_value("journal_entry", "");
        }
    },
    payment_account_name: propagate_to_child("payment_account_name"),
    payment_account: propagate_to_child("payment_account"),
    employee: propagate_to_child("employee"),
    project: propagate_to_child("project"),
    cost_center: propagate_to_child("cost_center"),
    refresh: function (frm) {
        set_expense_queries(frm);
        update_child_readonly(frm);
        if (frm.doc.journal_entry) {
            frm.add_custom_button(__("View Ledger"), function () {
                frappe.set_route("query-report", "General Ledger", {
                    voucher_no: frm.doc.journal_entry,
                    group_by: "Group by Voucher (Consolidated)",
                });
            });
        }
    }
});
frappe.ui.form.on("Expense Entry Table", {
    expense_entry_table_add(frm, cdt, cdn) {
        let defaults = ["cost_center", "project", "employee", "payment_account", "payment_account_name"];
        defaults.forEach(f => {
            frappe.model.set_value(cdt, cdn, f, frm.doc[f]);
        });
    },
})

function set_expense_queries(frm) {
    /* Employee filter */
    frm.set_query("employee", () => {
        return { filters: { company: frm.doc.company, status: "Active" } };
    });

    /* Mode of payment filter */
    frm.set_query("payment_account", () => {
        return {
            filters: {
                account_type: ["in", ["Bank", "Cash"]],
                is_group: 0,
                company: frm.doc.company,
            },
        };
    });

    /* Expense account filter */
    frm.fields_dict.expense_entry_table.grid.get_field("expense_account").get_query = () => ({
        filters: { is_group: 0, root_type: "Expense", company: frm.doc.company },
    });

    /* Child — mode_of_payment_account filter */
    frm.fields_dict.expense_entry_table.grid.get_field("payment_account").get_query = () => ({
        filters: {
            account_type: ["in", ["Bank", "Cash"]],
            is_group: 0,
            company: frm.doc.company,
        },
    });
}

function propagate_to_child(field) {
    return function (frm) {
        if (!frm.doc[field] || !frm.doc.expense_entry_table) return;

        let doctype = frm.doc.expense_entry_table[0].doctype;
        frm.doc.expense_entry_table.forEach(r => {
            frappe.model.set_value(doctype, r.name, field, frm.doc[field]);
        });

        update_child_readonly(frm);
    };
}

function update_child_readonly(frm) {
    const fields = ["payment_account_name", "payment_account", "employee", "project", "cost_center"];
    fields.forEach(f => {
        frm.fields_dict.expense_entry_table.grid.update_docfield_property(
            f,
            "read_only",
            frm.doc[f] ? 1 : 0
        );
    });
}