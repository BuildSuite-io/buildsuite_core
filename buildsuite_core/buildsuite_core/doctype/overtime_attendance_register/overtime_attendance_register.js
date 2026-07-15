// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Overtime Attendance Register", {
    validate: function(frm){
		if(!frm.doc.overtime_rate && frm.doc.overtime_rate == 0){
			const hasPermission = frappe.perm.has_perm("Employee", 0, "read");
			if(hasPermission){
				let d = new frappe.ui.Dialog({
					title: 'Update Wage',
					fields: [
						{
							label: 'Wage',
							fieldname: 'wage',
							fieldtype: 'Currency',
							reqd :1
						},
					],
					size: 'small', // small, large, extra-large 
					primary_action_label: 'Save',
					primary_action(values) {
						frappe.call({
						method:"buildsuite_core.buildsuite_core.doctype.overtime_attendance_register.overtime_attendance_register.update_wage",
						args:{
							'employee_id': frm.doc.employee,
							'wage':values.wage
						},
						callback(r){
							frm.set_value("overtime_rate",values.wage)
							d.hide()
						}
						
						})
					}
				});
				d.show();
			}else{
				frappe.throw(__('Overtime Wage is not update, Contact Admin to update.'))
			}
		}
	},
    has_permission: function (doctype, docname, perm_type, callback) {
		return frappe.call({
			type: "GET",
			method: "frappe.client.has_permission",
			no_spinner: true,
			args: { doctype: doctype, docname: docname, perm_type: perm_type },
			callback: function (r) {
				if (!r.exc && r.message.has_permission) {
					if (callback) {
						return callback(r);
					}
				}
			},
		});
	},
});
