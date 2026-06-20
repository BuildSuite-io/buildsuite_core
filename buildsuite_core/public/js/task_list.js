frappe.listview_settings["Task"] = {
	add_fields: [
		"project",
		"task_status",
		"priority",
		"exp_start_date",
		"exp_end_date",
		"progress",
	],

	filters: [["task_status", "=", "Yet To Start"]],

	get_indicator: function (doc) {
		const colors = {
			"Yet To Start": "orange",
			"In Progress": "blue",
			Working: "yellow",
			"Pending Review": "purple",
			"In Delay": "red",
			Completed: "green",
			Cancelled: "gray",
			Template: "darkgrey",
		};

		return [
			__(doc.task_status),
			colors[doc.task_status] || "gray",
			"task_status,=," + doc.task_status,
		];
	},

	onload: function (listview) {
		const method = "buildsuite_core.utils.task.set_multiple_status";

		listview.page.add_menu_item(__("Set as Yet To Start"), function () {
			listview.call_for_selected_items(method, {
				task_status: "Yet To Start",
			});
		});

		listview.page.add_menu_item(__("Set as Completed"), function () {
			listview.call_for_selected_items(method, {
				task_status: "Completed",
			});
		});
	},
};
