// Live-data context for Insights (first layer). Fetches the Core-5 datasets —
// Projects, Tasks, Stages, Subcontractor Bills, Purchase Orders — and shapes them
// into the `store`-like object the engine (data/insightEngine.js) reads. Only the
// datasets the persona may read are fetched (auto is gated on canRead), so the
// surface never asks for data the role can't see. Browser-side crunching: the
// engine runs over these arrays in memory.
import { computed } from "vue";

import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { usePermissions } from "@/composables/usePermissions";

const toArr = (res) =>
	Array.isArray(res.data) ? res.data : Array.isArray(res.data?.value) ? res.data.value : [];

export function useInsightsData() {
	const store = useDataStore();
	const adapter = createDataAdapter(store);
	const { canRead } = usePermissions();

	const can = {
		projects: canRead("project"),
		tasks: canRead("task"),
		stages: canRead("stagePlanning"),
		subBills: canRead("subcontractorBill"),
		purchaseOrders: canRead("purchaseOrder"),
	};

	// pageLength 0 = all rows (the engine crunches the full set in-browser).
	const projectsRes = adapter.list("Project", {
		fields: [
			"name",
			"project_name",
			"custom_project_id",
			"parent_project",
			"project_status",
			"company",
			"expected_start_date",
		],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.projects,
	});
	const tasksRes = adapter.list("Task", {
		fields: ["name", "subject", "project", "task_status", "status", "progress", "priority", "exp_end_date"],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.tasks,
	});
	const stagesRes = adapter.list("Stage Planning", {
		fields: ["name", "stage_name", "project", "workflow_state", "planned_end", "planned_start"],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.stages,
	});
	const subBillsRes = adapter.list("Subcontractor Bill", {
		fields: ["name", "project", "subcontractor", "subcontractor_name", "date", "status", "gross"],
		filters: { docstatus: ["<", 2] }, // exclude cancelled
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.subBills,
	});
	const poRes = adapter.list("Purchase Order", {
		fields: ["name", "supplier", "supplier_name", "status", "grand_total", "transaction_date", "project"],
		filters: { docstatus: ["<", 2] },
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.purchaseOrders,
	});

	const projects = computed(() =>
		toArr(projectsRes).map((p) => ({
			...p,
			id: p.name,
			name: p.project_name || p.name,
			code: p.custom_project_id || "",
			parentId: p.parent_project || null,
		}))
	);
	const projectMap = computed(() => {
		const m = {};
		for (const p of projects.value) m[p.id] = p;
		return m;
	});

	// The engine's `store`: live rows + project helpers + per-dataset read gates.
	const ctx = computed(() => ({
		projects: projects.value,
		rootProjects: projects.value.filter((p) => !p.parentId),
		projectById: (id) => projectMap.value[id] || null,
		tasks: toArr(tasksRes),
		stagePlannings: toArr(stagesRes),
		subBills: toArr(subBillsRes),
		purchaseOrders: toArr(poRes),
		canReadProjects: can.projects,
		canReadTasks: can.tasks,
		canReadStages: can.stages,
		canReadSubBills: can.subBills,
		canReadPurchaseOrders: can.purchaseOrders,
	}));

	const resources = [projectsRes, tasksRes, stagesRes, subBillsRes, poRes];
	const loading = computed(() => resources.some((r) => r.loading));

	return { ctx, loading };
}
