frappe.ui.form.on("Task", {
    refresh: function(frm) {
        frm.set_query("work_package", function() {
            return {
                filters: {
                    project: frm.doc.project
                }
            };
        });
    },
    onload: function(frm) {
        frm.set_query("work_package", function() {
            return {
                filters: {
                    project: frm.doc.project
                }
            };
        });
    }
})