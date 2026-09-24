// THE tab catalogue for the Project detail page — one definition read by three surfaces: the page
// that renders the tabs, the site-wide Project Settings page, and the per-project override in the
// project view's "..." menu.
//
// OVERVIEW IS DELIBERATELY NOT HERE. It is the landing tab and the fallback the page uses when the
// active tab disappears, so a project with it switched off would render nothing. It is always shown
// and never offered as a choice.
//
// `count` is NOT here: each count is a component-local computed over the project's own children,
// mapped on when the page builds the row. Keep in step with api/project_settings.PROJECT_TABS.
export const PROJECT_TABS = [
	{ id: "subprojects", label: "Subprojects", desc: 'Child projects under this one. Also needs "Allow subprojects" on the project itself.' },
	{ id: "work-packages", label: "Work Packages", desc: "The cost and control breakdown under the project." },
	{ id: "tasks", label: "Tasks", desc: "Every task on the project and its subprojects." },
	{ id: "stage-planning", label: "Stage Planning", desc: "Time-phased stages, their approval state and linked tasks." },
	{ id: "boq", label: "BOQ", desc: "Bill of quantities revisions priced for this project." },
	{ id: "scos", label: "Scope Changes", desc: "Scope change orders raised against the project." },
	{ id: "attachments", label: "Attachments", desc: "Drawings, contracts and permits held on the project record." },
	{ id: "team", label: "Team", desc: "People assigned to the project alongside the project manager." },
];

export const PROJECT_TAB_IDS = PROJECT_TABS.map((t) => t.id);
