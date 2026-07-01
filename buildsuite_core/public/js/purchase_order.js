frappe.ui.form.on('Purchase Order', {
    onload: function (frm) {
        ['schedule_date'].forEach(field => {
          frappe.ui.form.on('Purchase Order', {
            [field]: function (frm) {
              if (!frm.doc.items) return;
              frm.doc.items.forEach(row => {
                row[field] = frm.doc[field];
              });
        
              frm.refresh_field('items');
            }
          });
        });
    },
    schedule_date:function(frm){
    ['schedule_date'].forEach(field => {
          frappe.ui.form.on('Purchase Order', {
            [field]: function (frm) {
              if (!frm.doc.items) return;
              frm.doc.items.forEach(row => {
                row[field] = frm.doc[field];
              });
        
              frm.refresh_field('items');
            }
          });
        });
    },
    project:function(frm){
        if (frm.doc.project){
            if(frm.doc.items){
                frm.doc.items.forEach(item => {
                    frappe.model.set_value(item.doctype, item.name, 'project', frm.doc.project);
                    
                });
                frm.refresh_field('items');

            }
            frappe.call({
                method: "buildsuite_core.utils.stock_entry.get_warehouse_from_project",
                args: {
                    project: frm.doc.project,
                },
                freeze: true,
                callback: function (r) {
                    if (r.message) {
                        if(frm.doc.items){
                            frm.doc.items.forEach(item => {
                               frappe.model.set_value(item.doctype, item.name, 'warehouse', r.message);
                            });
                            frm.refresh_field('items');

                        }
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

frappe.ui.form.on("Purchase Order Item", {
    amount: function (frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        if (item.qty && item.amount) {
            item.__manual_amount = true;
            frappe.model.set_value(cdt, cdn, "rate", flt(item.amount / item.qty, precision("rate", item)));
            frappe.model.set_value(cdt, cdn, "custom_amout", item.amount);
        }
    }
});