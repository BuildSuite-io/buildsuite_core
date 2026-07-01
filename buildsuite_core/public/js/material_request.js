frappe.ui.form.on('Material Request', {
    onload: function (frm) {
        ['schedule_date'].forEach(field => {
          frappe.ui.form.on('Material Request', {
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
          frappe.ui.form.on('Material Request', {
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
    refresh:function(frm){
        frm.set_query('warehouse', 'items', function () {
			return {
					filters: { 'project': frm.doc.project,'is_group':0}
				}
		});
        frm.remove_custom_button("Purchase Order","Create")
        if (frm.doc.material_request_type === "Purchase"&&(frm.doc.per_ordered != 100 && frm.doc.docstatus==1)) {
            frm.add_custom_button(__("Purchase Order"), function () {
                frappe.model.open_mapped_doc({
                    method: "buildsuite_core.utils.material_request.create_purchase_order",
                    frm: frm,
                    run_link_triggers: true
                });
            }, __('Create'))
        }
    },
    project:function(frm){
        console.log("eiueyy")
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
    }
})
frappe.ui.form.on('Material Request Item', {
    item_code :function(frm, cdt, cdn){
        frappe.model.set_value(cdt, cdn, "project", frm.doc.project);
    },
    // item_code: function(frm, cdt, cdn){
    //     console.log("description")
    //     var row = locals[cdt][cdn];
    //     if (row.description==row.item_name){
    //         frappe.model.set_value(cdt, cdn, "description", null);
    //     }
    // },
    project: function(frm, cdt, cdn){
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "project");
	},
})