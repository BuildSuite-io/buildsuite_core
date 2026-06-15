frappe.ui.form.on("Task", {
    refresh: function(frm) {
        frm.set_query("work_package", function() {
            return {
                filters: {
                    project: frm.doc.project
                }
            };
        });
        if (frm.doc.task_status) {

            const colors = {
                "Yet To Start": "orange",
                "In Progress": "blue",
                "Completed": "green",
                "Cancelled": "gray",
                "Pending Review": "yellow",
                "In Delay": "red",
            };
            console.log(colors[frm.doc.task_status]);
            frm.page.set_indicator(
                __(frm.doc.task_status),
                colors[frm.doc.task_status] || "blue"
            );
        }
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