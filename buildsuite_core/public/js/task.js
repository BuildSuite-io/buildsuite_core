frappe.ui.form.on("Task", {
    refresh: function(frm) {
        frm.set_query("custom_work_package", function() {
            return {
                filters: {
                    project: frm.doc.project
                }
            };
        });
    }
})