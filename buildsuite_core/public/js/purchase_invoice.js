frappe.ui.form.on('Purchase Invoice', {
	project:function(frm){
        if (frm.doc.project){
            if(frm.doc.items){
                frm.doc.items.forEach(item => {
                    frappe.model.set_value(item.doctype, item.name, 'project', frm.doc.project);
                });
                frm.refresh_field('items');
            }
		}
	},
    refresh(frm){
        frm.set_query('item_tax_template', 'items', function (doc, cdt, cdn) {
            var item = frappe.get_doc(cdt, cdn);

            if(!item.item_code) {
                return doc.company ? {filters: {company: doc.company, custom_purpose:"Sales"}} : {};
            } else {
                let filters = {
                    'item_code': item.item_code,
                    'valid_from': ["<=", doc.transaction_date || doc.bill_date || doc.posting_date],
                    'item_group': item.item_group,
                    'custom_purpose':"Purchase",
                }

                if (doc.tax_category)
                    filters['tax_category'] = doc.tax_category;
                if (doc.company)
                    filters['company'] = doc.company;
                return {
                    query: "buildsuite_core.utils.purchase_order.get_tax_template",
                    filters: filters
                }
            }
                
		});
    },
})