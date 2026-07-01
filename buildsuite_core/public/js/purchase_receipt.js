frappe.ui.form.on('Purchase Receipt', {
    project:function(frm){
        if (frm.doc.project){
            if(frm.doc.items){
                frm.doc.items.forEach(item => {
                    frappe.model.set_value(item.doctype, item.name, 'project', frm.doc.project);
                });
                frm.refresh_field('items');
            }
           frappe.call({
            method:'buildsuite_core.utils.stock_entry.get_warehouse_from_project',
            args:{
                'project':frm.doc.project
            },
            callback: function (r) {
                if(r.message){
                    frm.set_value("set_warehouse",r.message)
                }
            }
           })
        }else{
            frm.set_value("set_warehouse",null)
        }
    },
    refresh(frm){
        frm.set_query('warehouse', 'items', function () {
			return {
					filters: { 'project': frm.doc.project,'is_group':0}
				}
		});
        frm.set_query('rejected_warehouse', 'items', function () {
			return {
					filters: { 'project': frm.doc.project,'is_group':0}
				}
		});
        frm.set_query('from_warehouse', 'items', function () {
			return {
					filters: { 'project': frm.doc.project,'is_group':0}
				}
		});
        frm.set_query('rejected_warehouse',  function () {
            return {
                filters: { 'project': frm.doc.project,'is_group':0}
            }
        })
        frm.set_query('set_warehouse',  function () {
            return {
                filters: { 'project': frm.doc.project,'is_group':0}
            }
        })
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
    }
})