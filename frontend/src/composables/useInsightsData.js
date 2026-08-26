// Live-data context for Insights. Fetches every dataset the engine
// (data/insightEngine.js) can query and shapes them into the `store`-like object
// it reads. Only the datasets the persona may read are fetched (auto is gated on
// canRead), so the surface never asks for data the role can't see. Browser-side
// crunching: the engine runs over these arrays in memory (pageLength 0 = all rows).
//
// LINE-level datasets (receipts / consumption / expenses / attendance) fetch the
// child DocType directly (child rows carry `parent`) plus their header, then join
// by parent name in `ctx` so the engine sees one flat row per line.
import { computed, ref } from "vue";

import { frappeRequest } from "frappe-ui-frappe-request";
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
		progress: canRead("taskProgressEntry"),
		workPackages: canRead("workPackage"),
		scos: canRead("sco"),
		purchaseOrders: canRead("purchaseOrder"),
		receipts: canRead("purchaseReceipt"),
		consumption: canRead("materialConsumption"),
		items: canRead("item"),
		workOrders: canRead("subcontractorWorkOrder"),
		subBills: canRead("subcontractorBill"),
		measurementBooks: canRead("measurementBook"),
		invoices: canRead("salesInvoice"),
		bills: canRead("supplierBill"),
		expenses: canRead("expense"),
		pettyCash: canRead("pettyCash"),
		attendance: canRead("fieldAttendance"),
		machineryUsage: canRead("machineryUsage"),
		fieldEmployees: canRead("fieldEmployee"),
	};

	// --- Core-5 (unchanged) ------------------------------------------------
	const projectsRes = adapter.list("Project", {
		fields: ["name", "project_name", "custom_project_id", "parent_project", "project_status", "company", "expected_start_date"],
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
		filters: { docstatus: ["<", 2] },
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

	// --- Flat (header-level) datasets -------------------------------------
	const progressRes = adapter.list("Task Progress Entry", {
		fields: ["name", "task", "entry_date", "cumulative_progress", "skilled", "unskilled", "blocker"],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.progress,
	});
	const wpRes = adapter.list("Work Package", {
		fields: ["name", "project", "code", "work_package_name", "status", "progress", "start_date", "end_date", "budget"],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.workPackages,
	});
	const scoRes = adapter.list("Scope Change Order", {
		fields: ["name", "project", "project_name", "title", "type", "impact", "status", "raised_date"],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.scos,
	});
	const woRes = adapter.list("Subcontractor Work Order", {
		fields: ["name", "subcontractor", "subcontractor_name", "project", "date", "delivery_type", "total_value"],
		filters: { docstatus: ["<", 2] },
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.workOrders,
	});
	const mbRes = adapter.list("Measurement Book", {
		fields: ["name", "work_order", "project", "date", "status", "measured_total"],
		filters: { docstatus: ["<", 2] },
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.measurementBooks,
	});
	const invoiceRes = adapter.list("Sales Invoice", {
		fields: ["name", "customer", "customer_name", "project", "posting_date", "grand_total", "status"],
		filters: { docstatus: ["<", 2] },
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.invoices,
	});
	const billRes = adapter.list("Purchase Invoice", {
		fields: ["name", "supplier", "supplier_name", "project", "posting_date", "grand_total", "status"],
		filters: { docstatus: ["<", 2] },
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.bills,
	});
	const pettyCashRes = adapter.list("Petty Cash Request", {
		fields: ["name", "project", "requested_by", "request_date", "amount", "status", "purpose"],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.pettyCash,
	});
	const itemsRes = adapter.list("Item", {
		fields: ["name", "item_name", "item_group", "stock_uom", "standard_rate", "disabled"],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.items,
	});
	const machineryUsageRes = adapter.list("Machinery Usage", {
		fields: ["name", "machine", "project", "date", "quantity", "unit", "rate", "fuel_cost"],
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.machineryUsage,
	});
	// Machine link resolves to a hashed docname; fetch its display name for the dimension label.
	const machineryRes = adapter.list("Machinery", {
		fields: ["name", "machinery_name"],
		pageLength: 0,
		auto: can.machineryUsage,
	});
	const fieldEmpRes = adapter.list("Employee", {
		fields: ["name", "employee_name", "custom_trade", "custom_wage", "custom_contractor", "status", "date_of_joining"],
		filters: { is_labour: 1 },
		pageLength: 0,
		orderBy: "modified desc",
		auto: can.fieldEmployees,
	});

	// --- LINE-level datasets: fetched via a backend endpoint --------------
	// Child DocTypes carry no standalone read permission, so a direct client get_list on them
	// 403s. buildsuite_core.api.insights.line_dataset reads parent+child server-side under the
	// caller's PARENT read permission and returns the flat row shape the engine expects.
	const lineData = ref({ receiptLines: [], consumptionLines: [], expenses: [], attendance: [] });
	const lineLoading = ref(false);
	async function fetchLine(name) {
		try {
			const rows = await frappeRequest({
				url: "buildsuite_core.api.insights.line_dataset",
				params: { dataset: name },
			});
			lineData.value = { ...lineData.value, [name]: Array.isArray(rows) ? rows : [] };
		} catch {
			/* leave this dataset empty — the surface just won't offer it */
		}
	}
	const lineJobs = [
		[can.receipts, "receiptLines"],
		[can.consumption, "consumptionLines"],
		[can.expenses, "expenses"],
		[can.attendance, "attendance"],
	].filter(([ok]) => ok);
	if (lineJobs.length) {
		lineLoading.value = true;
		Promise.allSettled(lineJobs.map(([, name]) => fetchLine(name))).finally(() => {
			lineLoading.value = false;
		});
	}

	// --- Shaped context ----------------------------------------------------
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
	const taskProjectMap = computed(() => {
		const m = {};
		for (const t of toArr(tasksRes)) m[t.name] = t.project;
		return m;
	});
	const machineryMap = computed(() => {
		const m = {};
		for (const r of toArr(machineryRes)) m[r.name] = r.machinery_name || r.name;
		return m;
	});

	const ctx = computed(() => ({
		projects: projects.value,
		rootProjects: projects.value.filter((p) => !p.parentId),
		projectById: (id) => projectMap.value[id] || null,
		taskProject: (taskId) => taskProjectMap.value[taskId] || null,
		machineryName: (id) => machineryMap.value[id] || id || "—",
		// raw / flattened rows
		tasks: toArr(tasksRes),
		stagePlannings: toArr(stagesRes),
		taskProgressEntries: toArr(progressRes),
		workPackages: toArr(wpRes),
		scos: toArr(scoRes),
		purchaseOrders: toArr(poRes),
		receiptLines: lineData.value.receiptLines,
		consumptionLines: lineData.value.consumptionLines,
		items: toArr(itemsRes),
		workOrders: toArr(woRes),
		subBills: toArr(subBillsRes),
		measurementBooks: toArr(mbRes),
		invoices: toArr(invoiceRes),
		bills: toArr(billRes),
		expenses: lineData.value.expenses,
		pettyCash: toArr(pettyCashRes),
		attendance: lineData.value.attendance,
		machineryUsage: toArr(machineryUsageRes),
		fieldEmployees: toArr(fieldEmpRes),
		// read gates
		canReadProjects: can.projects,
		canReadTasks: can.tasks,
		canReadStages: can.stages,
		canReadProgress: can.progress,
		canReadWorkPackages: can.workPackages,
		canReadScos: can.scos,
		canReadPurchaseOrders: can.purchaseOrders,
		canReadReceipts: can.receipts,
		canReadConsumption: can.consumption,
		canReadItems: can.items,
		canReadWorkOrders: can.workOrders,
		canReadSubBills: can.subBills,
		canReadMeasurementBooks: can.measurementBooks,
		canReadInvoices: can.invoices,
		canReadBills: can.bills,
		canReadExpenses: can.expenses,
		canReadPettyCash: can.pettyCash,
		canReadAttendance: can.attendance,
		canReadMachineryUsage: can.machineryUsage,
		canReadFieldEmployees: can.fieldEmployees,
	}));

	const resources = [
		projectsRes, tasksRes, stagesRes, subBillsRes, poRes, progressRes, wpRes, scoRes, woRes, mbRes,
		invoiceRes, billRes, pettyCashRes, itemsRes, machineryUsageRes, machineryRes, fieldEmpRes,
	];
	const loading = computed(() => lineLoading.value || resources.some((r) => r.loading));

	return { ctx, loading };
}
