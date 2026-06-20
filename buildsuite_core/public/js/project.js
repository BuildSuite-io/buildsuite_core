// BuildSuite Core — Project form extensions
// Renders related sub-records (Subprojects, Work Packages, Tasks, Stage Plannings)
// as inline tables inside the custom tab HTML fields on the Project form.
// Uses Frappe Quick Entry dialogs for new-record creation and standard Frappe
// CSS classes throughout so the UI blends with the native ERPNext look.

frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.doc.__islocal) return;

		render_subprojects(frm);
		render_work_packages(frm);
		render_tasks(frm);
		render_stage_plannings(frm);
	},
});

// ──────────────────────────────────────────────────────────────────────────────
// Shared helpers
// ──────────────────────────────────────────────────────────────────────────────

function status_indicator(status) {
	const map = {
		Active: "blue",
		Open: "blue",
		Working: "blue",
		"In Progress": "orange",
		Planned: "gray",
		Completed: "green",
		"On Hold": "yellow",
		Cancelled: "red",
	};
	const color = map[status] || "gray";
	return `<span class="indicator-pill ${color}">${status || "—"}</span>`;
}

function progress_bar(pct) {
	const val = pct || 0;
	return `<div style="display:flex;align-items:center;gap:6px;">
		<div class="progress" style="flex:1;height:6px;margin-bottom:0;border-radius:3px;">
			<div class="progress-bar" role="progressbar" style="width:${val}%;"></div>
		</div>
		<span class="text-muted" style="font-size:11px;min-width:30px;">${val}%</span>
	</div>`;
}

function make_table(columns, rows, empty_msg) {
	if (!rows || !rows.length) {
		return `<p class="text-muted" style="padding:10px 0;font-size:12px;">${empty_msg}</p>`;
	}
	const ths = columns
		.map(
			(c) =>
				`<th class="text-muted" style="font-size:11px;font-weight:600;padding:6px 8px;">${c.label}</th>`
		)
		.join("");
	const trs = rows
		.map((row) => {
			const tds = columns
				.map((c) => {
					const val = c.render ? c.render(row) : row[c.key] || "—";
					return `<td style="padding:6px 8px;vertical-align:middle;font-size:12px;">${val}</td>`;
				})
				.join("");
			return `<tr>${tds}</tr>`;
		})
		.join("");
	return `<table class="table table-hover" style="width:100%;margin:0;">
		<thead><tr>${ths}</tr></thead>
		<tbody>${trs}</tbody>
	</table>`;
}

/**
 * Inject HTML into an HTML field and bind post-render events.
 * @param {Object} frm
 * @param {string} fieldname
 * @param {string} html
 * @param {Function} [bind] - receives field.$wrapper after DOM update
 */
function set_html_and_bind(frm, fieldname, html, bind) {
	const field = frm.fields_dict[fieldname];
	if (!field) return;
	field.$wrapper.html(html);
	if (bind) bind(field.$wrapper);
}

function make_new_doc_with_defaults(doctype, defaults) {
	const doc = frappe.model.get_new_doc(doctype, null, null, true);
	Object.assign(doc, defaults || {});
	return doc;
}

function get_project_scope(frm) {
	const project_labels = {
		[frm.doc.name]: frm.doc.project_name || frm.doc.name,
	};

	if (!frm.doc.is_group) {
		return Promise.resolve({
			project_names: [frm.doc.name],
			project_labels,
		});
	}

	return frappe.db
		.get_list("Project", {
			filters: { parent_project: frm.doc.name },
			fields: ["name", "project_name"],
			limit: 500,
		})
		.then((rows) => {
			rows.forEach((row) => {
				project_labels[row.name] = row.project_name || row.name;
			});

			return {
				project_names: [frm.doc.name, ...rows.map((row) => row.name)],
				project_labels,
			};
		});
}

// ──────────────────────────────────────────────────────────────────────────────
// Subprojects tab
// ──────────────────────────────────────────────────────────────────────────────

function render_subprojects(frm) {
	frappe.db
		.get_list("Project", {
			filters: { parent_project: frm.doc.name },
			fields: [
				"name",
				"project_name",
				"custom_project_id",
				"status",
				"percent_complete",
				"expected_end_date",
			],
			limit: 50,
		})
		.then((rows) => {
			const columns = [
				{
					label: "Project ID",
					render: (r) =>
						`<a href="/app/project/${r.name}">${r.custom_project_id || r.name}</a>`,
				},
				{ label: "Name", key: "project_name" },
				{ label: "Status", render: (r) => status_indicator(r.status) },
				{ label: "Progress", render: (r) => progress_bar(r.percent_complete) },
				{ label: "End Date", key: "expected_end_date" },
			];
			const html = `
				<div class="d-flex align-items-center justify-content-between" style="margin-bottom:10px;">
					<span class="text-muted" style="font-size:12px;">${rows.length} sub-project(s)</span>
					<button class="btn btn-primary btn-sm bs-add-btn">
						${frappe.utils.icon("add", "xs")} Sub-project
					</button>
				</div>
				${make_table(columns, rows, "No sub-projects linked to this project.")}`;
			set_html_and_bind(frm, "custom_subprojects_html", html, ($w) => {
				$w.find(".bs-add-btn").on("click", () => {
					const new_doc = make_new_doc_with_defaults("Project", {
						parent_project: frm.doc.name,
					});
					frappe.ui.form.make_quick_entry(
						"Project",
						() => render_subprojects(frm),
						null,
						new_doc,
						true
					);
				});
			});
		});
}

// ──────────────────────────────────────────────────────────────────────────────
// Work Packages tab
// ──────────────────────────────────────────────────────────────────────────────

function render_work_packages(frm) {
	frappe.db
		.get_list("Work Package", {
			filters: { project: frm.doc.name },
			fields: ["name", "code", "work_package_name", "status", "progress", "end_date"],
			limit: 100,
		})
		.then((rows) => {
			const columns = [
				{
					label: "Code",
					render: (r) => `<a href="/app/work-package/${r.name}">${r.code || r.name}</a>`,
				},
				{ label: "Work Package", key: "work_package_name" },
				{ label: "Status", render: (r) => status_indicator(r.status) },
				{ label: "Progress", render: (r) => progress_bar(r.progress) },
				{ label: "End Date", key: "end_date" },
			];
			const html = `
				<div class="d-flex align-items-center justify-content-between" style="margin-bottom:10px;">
					<span class="text-muted" style="font-size:12px;">${rows.length} work package(s)</span>
					<button class="btn btn-primary btn-sm bs-add-btn">
						${frappe.utils.icon("add", "xs")} Work Package
					</button>
				</div>
				${make_table(columns, rows, "No work packages linked to this project.")}`;
			set_html_and_bind(frm, "custom_work_packages_html", html, ($w) => {
				$w.find(".bs-add-btn").on("click", () => {
					const new_doc = make_new_doc_with_defaults("Work Package", {
						project: frm.doc.name,
					});
					frappe.ui.form.make_quick_entry(
						"Work Package",
						() => render_work_packages(frm),
						null,
						new_doc
					);
				});
			});
		});
}

// ──────────────────────────────────────────────────────────────────────────────
// Tasks tab
// ──────────────────────────────────────────────────────────────────────────────

function render_tasks(frm) {
	get_project_scope(frm).then(({ project_names, project_labels }) => {
		const task_filters = {
			project: project_names.length === 1 ? project_names[0] : ["in", project_names],
		};

		frappe.db
			.get_list("Task", {
				filters: task_filters,
				fields: [
					"name",
					"subject",
					"project",
					"status",
					"priority",
					"exp_end_date",
					"progress",
				],
				limit: 100,
			})
			.then((rows) => {
				const columns = [
					{
						label: "Task",
						render: (r) => `<a href="/app/task/${r.name}">${r.subject || r.name}</a>`,
					},
					...(frm.doc.is_group
						? [
								{
									label: "Project",
									render: (r) => project_labels[r.project] || r.project || "-",
								},
						  ]
						: []),
					{ label: "Status", render: (r) => status_indicator(r.status) },
					{ label: "Priority", render: (r) => status_indicator(r.priority) },
					{ label: "Progress", render: (r) => progress_bar(r.progress) },
					{ label: "Due Date", key: "exp_end_date" },
				];
				const html = `
				<div class="d-flex align-items-center justify-content-between" style="margin-bottom:10px;">
					<span class="text-muted" style="font-size:12px;">${rows.length} task(s)</span>
					<button class="btn btn-primary btn-sm bs-add-btn">
						${frappe.utils.icon("add", "xs")} Task
					</button>
				</div>
				${make_table(columns, rows, "No tasks linked to this project.")}`;
				set_html_and_bind(frm, "custom_tasks_html", html, ($w) => {
					$w.find(".bs-add-btn").on("click", () => {
						const new_doc = make_new_doc_with_defaults("Task", {
							project: frm.doc.name,
						});
						frappe.ui.form.make_quick_entry(
							"Task",
							() => render_tasks(frm),
							null,
							new_doc
						);
					});
				});
			});
	});
}

// ──────────────────────────────────────────────────────────────────────────────
// Stage Planning tab
// ──────────────────────────────────────────────────────────────────────────────

function render_stage_plannings(frm) {
	get_project_scope(frm).then(({ project_names, project_labels }) => {
		const stage_filters = {
			project: project_names.length === 1 ? project_names[0] : ["in", project_names],
		};

		frappe.db
			.get_list("Stage Planning", {
				filters: stage_filters,
				fields: [
					"name",
					"stage_name",
					"project",
					"planned_start",
					"planned_end",
					"planned_task_count",
					"planned_completion_pct",
				],
				limit: 100,
			})
			.then((rows) => {
				const columns = [
					{
						label: "Stage",
						render: (r) =>
							`<a href="/app/stage-planning/${r.name}">${r.stage_name}</a>`,
					},
					...(frm.doc.is_group
						? [
								{
									label: "Project",
									render: (r) => project_labels[r.project] || r.project || "-",
								},
						  ]
						: []),
					{ label: "Planned Start", key: "planned_start" },
					{ label: "Planned End", key: "planned_end" },
					{ label: "Tasks", key: "planned_task_count" },
					{
						label: "Planned Completion",
						render: (r) => progress_bar(r.planned_completion_pct),
					},
				];
				const html = `
				<div class="d-flex align-items-center justify-content-between" style="margin-bottom:10px;">
					<span class="text-muted" style="font-size:12px;">${rows.length} stage(s)</span>
					<button class="btn btn-primary btn-sm bs-add-btn">
						${frappe.utils.icon("add", "xs")} Stage
					</button>
				</div>
				${make_table(columns, rows, "No stage plans linked to this project.")}`;
				set_html_and_bind(frm, "custom_stage_planning_html", html, ($w) => {
					$w.find(".bs-add-btn").on("click", () => {
						const new_doc = make_new_doc_with_defaults("Stage Planning", {
							project: frm.doc.name,
						});
						frappe.ui.form.make_quick_entry(
							"Stage Planning",
							() => render_stage_plannings(frm),
							null,
							new_doc
						);
					});
				});
			});
	});
}
