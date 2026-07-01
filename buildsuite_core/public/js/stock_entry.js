frappe.provide("erpnext.stock");
frappe.provide("erpnext.accounts.dimensions");


frappe.ui.form.on('Stock Entry', {
	refresh:function(frm) {
        frm.set_query('stock_entry_type', () => {
            return {
                filters: {
                    'name': ["IN",['Material Receipt','Material Transfer','Material Issue']]
                }
            }
        })
        frm.set_query('from_warehouse',  function () {
            return {
                filters: { 'project': frm.doc.project,'is_group':0}
            }
        })
        frm.set_query('to_warehouse',  function () {
            return {
                filters: { 'project': frm.doc.project,'is_group':0}
            }
        })
        frm.set_query('s_warehouse', 'items', function () {
			return {
					filters: { 'project': frm.doc.project,'is_group':0}
				}
		});
        frm.set_query('t_warehouse', 'items', function () {
			return {
					filters: { 'project': frm.doc.project,'is_group':0}
				}
		});
    },
    stock_entry_type:function(frm){
        frm.set_value("project",null)
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
            method:'buildsuite_core.utils.stock_entry.get_warehouse_from_project',
            args:{
                'project':frm.doc.project
            },
            callback: function (r) {
                if(r.message){
                    if(frm.doc.purpose=="Material Issue"){
                        frm.set_value("from_warehouse",r.message)
                        frm.set_value("to_warehouse",null)
                    }
                    if(frm.doc.purpose=="Material Receipt"){
                        frm.set_value("to_warehouse",r.message)
                        frm.set_value("from_warehouse",null)
                    }
                }
            }
           })
        }else{
            frm.set_value("from_warehouse",null)
            frm.set_value("to_warehouse",null)
        }
    },
})

frappe.ui.form.on('Stock Entry Detail', {
    s_warehouse :function(frm, cdt, cdn){
        if(frm.doc.purpose=="Material Issue"){
            frappe.model.set_value(cdt, cdn, "t_warehouse", null);
        }
        frappe.model.set_value(cdt, cdn, "project", frm.doc.project);
    },
    t_warehouse:function(frm, cdt, cdn){
        if(frm.doc.purpose=="Material Receipt"){
            frappe.model.set_value(cdt, cdn, "s_warehouse", null);
        }
        frappe.model.set_value(cdt, cdn, "project", frm.doc.project);
    },
    project: function(frm, cdt, cdn){
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "project");
	},
})