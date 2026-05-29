// BuildSuite Core — Project form extensions
// Renders related sub-records (Subprojects, Work Packages, Tasks, Stage Plannings)
// as inline mini-lists inside the custom tab HTML fields on the Project form.

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

function status_badge(status) {
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

function add_new_btn(label, route) {
	return `<a href="${route}" class="btn btn-xs btn-default ml-2"
		style="font-size:11px;padding:2px 8px;">
		+ ${label}
	</a>`;
}

/**
 * Build a standard Frappe-styled table from column definitions and row data.
 * @param {Array<{label, key, render?}>} columns
 * @param {Array<Object>} rows
 * @param {string} emptyMsg
 */
function make_table(columns, rows, emptyMsg) {
	if (!rows || !rows.length) {
		return `<div class="text-muted" style="padding:12px 0;font-size:12px;">${emptyMsg}</div>`;
	}
	const header = columns
		.map((c) => `<th style="font-size:11px;font-weight:600;padding:6px 8px;">${c.label}</th>`)
		.join("");
	const body = rows
		.map((row) => {
			const cells = columns
				.map((c) => {
					const val = c.render ? c.render(row) : (row[c.key] || "—");
					return `<td style="font-size:12px;padding:6px 8px;vertical-align:middle;">${val}</td>`;
				})
				.join("");
			return `<tr>${cells}</tr>`;
		})
		.join("");
	return `
		<table class="table table-bordered" style="width:100%;border-collapse:collapse;">
			<thead style="background:var(--fg-color,#f4f5f6);">
				<tr>${header}</tr>
			</thead>
			<tbody>${body}</tbody>
		</table>`;
}

function set_html(frm, fieldname, html) {
	const field = frm.fields_dict[fieldname];
	if (field) {
		field.$wrapper.html(html);
	}
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
					key: "custom_project_id",
					render: (r) =>
						`<a href="/app/project/${r.name}" style="color:var(--primary)">${r.custom_project_id || r.name}</a>`,
				},
				{ label: "Name", key: "project_name" },
				{ label: "Status", key: "status", render: (r) => status_badge(r.status) },
				{
					label: "Progress",
					key: "percent_complete",
					render: (r) =>
						`<div style="display:flex;align-items:center;gap:6px;">
							<div style="flex:1;height:4px;background:#e2e8f0;border-radius:2px;">
								<div style="width:${r.percent_complete || 0}%;height:100%;background:var(--primary);border-radius:2px;"></div>
							</div>
							<span style="font-size:11px;min-width:28px;text-align:right;">${r.percent_complete || 0}%</span>
						</div>`,
				},
				{ label: "End Date", key: "expected_end_date" },
			];
			const newBtn = add_new_btn(
				"Sub-project",
				`/app/project/new-project-1?parent_project=${encodeURIComponent(frm.doc.name)}`
			);
			const table = make_table(columns, rows, "No sub-projects linked to this project.");
			set_html(
				frm,
				"custom_subprojects_html",
				`<div style="margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
					<span style="font-size:11px;color:var(--text-muted);">${rows.length} sub-project(s)</span>
					${newBtn}
				</div>${table}`
			);
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
					key: "code",
					render: (r) =>
						`<a href="/app/work-package/${r.name}" style="color:var(--primary)">${r.code || r.name}</a>`,
				},
				{ label: "Work Package", key: "work_package_name" },
				{ label: "Status", key: "status", render: (r) => status_badge(r.status) },
				{
					label: "Progress",
					key: "progress",
					render: (r) =>
						`<div style="display:flex;align-items:center;gap:6px;">
							<div style="flex:1;height:4px;background:#e2e8f0;border-radius:2px;">
								<div style="width:${r.progress || 0}%;height:100%;background:var(--primary);border-radius:2px;"></div>
							</div>
							<span style="font-size:11px;min-width:28px;text-align:right;">${r.progress || 0}%</span>
						</div>`,
				},
				{ label: "End Date", key: "end_date" },
			];
			const newBtn = add_new_btn(
				"Work Package",
				`/app/work-package/new-work-package-1?project=${encodeURIComponent(frm.doc.name)}`
			);
			const table = make_table(columns, rows, "No work packages linked to this project.");
			set_html(
				frm,
				"custom_work_packages_html",
				`<div style="margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
					<span style="font-size:11px;color:var(--text-muted);">${rows.length} work package(s)</span>
					${newBtn}
				</div>${table}`
			);
		});
}

// ──────────────────────────────────────────────────────────────────────────────
// Tasks tab
// ──────────────────────────────────────────────────────────────────────────────

function render_tasks(frm) {
	frappe.db
		.get_list("Task", {
			filters: { project: frm.doc.name },
			fields: ["name", "subject", "status", "priority", "exp_end_date", "progress"],
			limit: 100,
		})
		.then((rows) => {
			const columns = [
				{
					label: "Task",
					key: "subject",
					render: (r) =>
						`<a href="/app/task/${r.name}" style="color:var(--primary)">${r.subject || r.name}</a>`,
				},
				{ label: "Status", key: "status", render: (r) => status_badge(r.status) },
				{ label: "Priority", key: "priority", render: (r) => status_badge(r.priority) },
				{
					label: "Progress",
					key: "progress",
					render: (r) =>
						`<div style="display:flex;align-items:center;gap:6px;">
							<div style="flex:1;height:4px;background:#e2e8f0;border-radius:2px;">
								<div style="width:${r.progress || 0}%;height:100%;background:var(--primary);border-radius:2px;"></div>
							</div>
							<span style="font-size:11px;min-width:28px;text-align:right;">${r.progress || 0}%</span>
						</div>`,
				},
				{ label: "Due Date", key: "exp_end_date" },
			];
			const newBtn = add_new_btn(
				"Task",
				`/app/task/new-task-1?project=${encodeURIComponent(frm.doc.name)}`
			);
			const table = make_table(columns, rows, "No tasks linked to this project.");
			set_html(
				frm,
				"custom_tasks_html",
				`<div style="margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
					<span style="font-size:11px;color:var(--text-muted);">${rows.length} task(s)</span>
					${newBtn}
				</div>${table}`
			);
		});
}

// ──────────────────────────────────────────────────────────────────────────────
// Stage Planning tab
// ──────────────────────────────────────────────────────────────────────────────

function render_stage_plannings(frm) {
	frappe.db
		.get_list("Stage Planning", {
			filters: { project: frm.doc.name },
			fields: [
				"name",
				"stage_name",
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
					key: "stage_name",
					render: (r) =>
						`<a href="/app/stage-planning/${r.name}" style="color:var(--primary)">${r.stage_name}</a>`,
				},
				{ label: "Planned Start", key: "planned_start" },
				{ label: "Planned End", key: "planned_end" },
				{ label: "Task Count", key: "planned_task_count" },
				{
					label: "Planned Completion",
					key: "planned_completion_pct",
					render: (r) =>
						`<div style="display:flex;align-items:center;gap:6px;">
							<div style="flex:1;height:4px;background:#e2e8f0;border-radius:2px;">
								<div style="width:${r.planned_completion_pct || 0}%;height:100%;background:var(--primary);border-radius:2px;"></div>
							</div>
							<span style="font-size:11px;min-width:28px;text-align:right;">${r.planned_completion_pct || 0}%</span>
						</div>`,
				},
			];
			const newBtn = add_new_btn(
				"Stage",
				`/app/stage-planning/new-stage-planning-1?project=${encodeURIComponent(frm.doc.name)}`
			);
			const table = make_table(columns, rows, "No stage plans linked to this project.");
			set_html(
				frm,
				"custom_stage_planning_html",
				`<div style="margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
					<span style="font-size:11px;color:var(--text-muted);">${rows.length} stage(s)</span>
					${newBtn}
				</div>${table}`
			);
		});
}
