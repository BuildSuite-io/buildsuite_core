// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Assembly Component', {
    coefficient(frm, cdt, cdn) {
        recompute(frm, cdt, cdn)
    },
    resource(frm, cdt, cdn) {
        recompute(frm, cdt, cdn)
    },
    rate(frm, cdt, cdn) {
        recompute(frm, cdt, cdn)
    },
    components_remove(frm) {
        set_total(frm)
    },
})

function recompute(frm, cdt, cdn) {
    const row = locals[cdt][cdn]
    frappe.model.set_value(cdt, cdn, 'amount', (row.coefficient || 0) * (row.rate || 0))
    set_total(frm)
}

function set_total(frm) {
    const total = (frm.doc.components || []).reduce((sum, r) => sum + (r.amount || 0), 0)
    frm.set_value('rate_per_unit', total)
}
