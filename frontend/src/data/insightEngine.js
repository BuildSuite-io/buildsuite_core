// Insights — the query model behind the prompt box (first layer).
//
// HONESTY NOTE, read before extending. There is no model call. A prompt is
// matched LOCALLY — synonyms → a QuerySpec — and the spec is executed against
// live data fed in as `store` (see composables/useInsightsData.js). Every number
// a chart shows is a real record, and an unrecognised prompt says so.
//
// In production this same spec is what an LLM would emit: prompt → model →
// QuerySpec → the executor below, unchanged. Parser and executor are kept apart
// precisely so the half that gets replaced later (AI understanding) is one
// function. This file is ported almost verbatim from the prototype's engine; the
// only thing that changed for the live product is each dataset's rows/can/
// accessors, which now read real Frappe data instead of the mock store.
//
// QuerySpec:
//   { source, mode:'aggregate'|'list', measure, dimension,
//     filters:{project,from,to,values,min,max}, viz, sort, limit }

// ---------------------------------------------------------------------------
// Helpers shared by the dataset definitions
// ---------------------------------------------------------------------------
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function monthOf(iso) {
	if (!iso) return "—";
	const [y, m] = String(iso).slice(0, 7).split("-");
	return m ? `${MONTHS[Number(m) - 1]} ${y}` : "—";
}
const n = (v) => Number(v) || 0;
const pName = (s, id) => s.projectById(id)?.name || id || "—";

// ---------------------------------------------------------------------------
// Datasets — the first-layer cut: Projects, Tasks, Stages, Subcontractor Bills,
// Purchase Orders. Each declares can(store) so the surface only offers what the
// signed-in role may read. `rows(store)` returns live records; accessors read
// their real Frappe fields.
// ---------------------------------------------------------------------------
export const DATASETS = {
	projects: {
		label: "Projects",
		can: (s) => s.canReadProjects,
		words: ["project", "projects", "job", "jobs"],
		rows: (s) => s.rootProjects,
		date: (r) => r.expected_start_date,
		amount: () => 0,
		qty: () => 0,
		project: (r) => r.name,
		measures: ["count"],
		dims: {
			status: { label: "Status", get: (r) => r.project_status || "—" },
			company: { label: "Company", get: (r) => r.company || "—" },
		},
		list: {
			columns: [
				{ key: "name", label: "Project" },
				{ key: "code", label: "ID" },
				{ key: "status", label: "Status" },
			],
			row: (r) => ({
				name: r.project_name || r.name,
				code: r.custom_project_id || r.name,
				status: r.project_status || "—",
			}),
		},
	},
	tasks: {
		label: "Tasks",
		can: (s) => s.canReadTasks,
		words: ["task", "tasks", "activity", "activities"],
		rows: (s) => s.tasks,
		date: (r) => r.exp_end_date,
		amount: () => 0,
		qty: () => 0,
		project: (r) => r.project,
		measures: ["count"],
		dims: {
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			status: { label: "Status", get: (r) => r.task_status || r.status || "—" },
			priority: { label: "Priority", get: (r) => r.priority || "—" },
			month: { label: "Month", get: (r) => monthOf(r.exp_end_date) },
		},
		list: {
			columns: [
				{ key: "name", label: "Task" },
				{ key: "project", label: "Project" },
				{ key: "status", label: "Status" },
				{ key: "progress", label: "Progress", align: "right" },
			],
			row: (r, s) => ({
				name: r.subject || r.name,
				project: pName(s, r.project),
				status: r.task_status || r.status || "—",
				progress: `${n(r.progress)}%`,
			}),
		},
	},
	stages: {
		label: "Stages",
		can: (s) => s.canReadStages,
		words: ["stage", "stages", "stage plan", "stage planning"],
		rows: (s) => s.stagePlannings,
		date: (r) => r.planned_end,
		amount: () => 0,
		qty: () => 0,
		project: (r) => r.project,
		measures: ["count"],
		dims: {
			state: { label: "Approval state", get: (r) => r.workflow_state || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.planned_end) },
		},
		list: {
			columns: [
				{ key: "name", label: "Stage" },
				{ key: "project", label: "Project" },
				{ key: "end", label: "Planned end" },
				{ key: "state", label: "State" },
			],
			row: (r, s) => ({
				name: r.stage_name || r.name,
				project: pName(s, r.project),
				end: r.planned_end || "—",
				state: r.workflow_state || "—",
			}),
		},
	},
	subBills: {
		label: "Subcontractor bills",
		can: (s) => s.canReadSubBills,
		words: ["subcontractor bill", "subcontractor bills", "ra bill", "ra bills", "sub bill", "sub bills"],
		rows: (s) => s.subBills,
		date: (r) => r.date,
		amount: (r) => n(r.gross),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			subcontractor: { label: "Subcontractor", get: (r) => r.subcontractor_name || r.subcontractor || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			status: { label: "Status", get: (r) => r.status || "—" },
			month: { label: "Month", get: (r) => monthOf(r.date) },
		},
		list: {
			columns: [
				{ key: "name", label: "Bill" },
				{ key: "subcontractor", label: "Subcontractor" },
				{ key: "project", label: "Project" },
				{ key: "gross", label: "Gross", align: "right", money: true },
			],
			row: (r, s) => ({
				name: r.name,
				subcontractor: r.subcontractor_name || r.subcontractor || "—",
				project: pName(s, r.project),
				gross: n(r.gross),
			}),
		},
	},
	purchaseOrders: {
		label: "Purchase orders",
		can: (s) => s.canReadPurchaseOrders,
		words: ["purchase order", "purchase orders"],
		rows: (s) => s.purchaseOrders,
		date: (r) => r.transaction_date,
		amount: (r) => n(r.grand_total),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			supplier: { label: "Supplier", get: (r) => r.supplier_name || r.supplier || "—" },
			status: { label: "Status", get: (r) => r.status || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.transaction_date) },
		},
		list: {
			columns: [
				{ key: "name", label: "PO" },
				{ key: "supplier", label: "Supplier" },
				{ key: "status", label: "Status" },
				{ key: "total", label: "Total", align: "right", money: true },
			],
			row: (r) => ({
				name: r.name,
				supplier: r.supplier_name || r.supplier || "—",
				status: r.status || "—",
				total: n(r.grand_total),
			}),
		},
	},
	progress: {
		label: "Progress entries",
		can: (s) => s.canReadProgress,
		words: ["progress", "progress entries", "progress entry", "site report", "site reports", "daily report"],
		rows: (s) => s.taskProgressEntries,
		date: (r) => r.entry_date,
		amount: () => 0,
		qty: () => 0,
		project: (r, s) => s.taskProject(r.task),
		measures: ["count"],
		dims: {
			project: { label: "Project", get: (r, s) => pName(s, s.taskProject(r.task)) },
			month: { label: "Month", get: (r) => monthOf(r.entry_date) },
			blocker: { label: "Blocker", get: (r) => (r.blocker ? "Blocked" : "Clear") },
		},
		list: {
			columns: [
				{ key: "date", label: "Date" },
				{ key: "task", label: "Task" },
				{ key: "pct", label: "Progress", align: "right" },
				{ key: "project", label: "Project" },
			],
			row: (r, s) => ({
				date: r.entry_date || "—",
				task: r.task,
				pct: `${n(r.cumulative_progress)}%`,
				project: pName(s, s.taskProject(r.task)),
			}),
		},
	},
	workPackages: {
		label: "Work packages",
		can: (s) => s.canReadWorkPackages,
		words: ["work package", "work packages"],
		rows: (s) => s.workPackages,
		date: (r) => r.start_date,
		amount: (r) => n(r.budget),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			status: { label: "Status", get: (r) => r.status || "—" },
			month: { label: "Month", get: (r) => monthOf(r.start_date) },
		},
		list: {
			columns: [
				{ key: "name", label: "Work package" },
				{ key: "project", label: "Project" },
				{ key: "status", label: "Status" },
				{ key: "budget", label: "Budget", align: "right", money: true },
			],
			row: (r, s) => ({
				name: r.work_package_name || r.code || r.name,
				project: pName(s, r.project),
				status: r.status || "—",
				budget: n(r.budget),
			}),
		},
	},
	scos: {
		label: "Scope changes",
		can: (s) => s.canReadScos,
		words: ["scope change", "scope changes", "sco", "variation", "variations"],
		rows: (s) => s.scos,
		date: (r) => r.raised_date,
		amount: (r) => n(r.impact),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			status: { label: "Status", get: (r) => r.status || "—" },
			type: { label: "Type", get: (r) => r.type || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.raised_date) },
		},
		list: {
			columns: [
				{ key: "id", label: "SCO" },
				{ key: "title", label: "Title" },
				{ key: "project", label: "Project" },
				{ key: "status", label: "Status" },
				{ key: "impact", label: "Impact", align: "right", money: true },
			],
			row: (r, s) => ({
				id: r.name,
				title: r.title || "—",
				project: pName(s, r.project),
				status: r.status || "—",
				impact: n(r.impact),
			}),
		},
	},
	workOrders: {
		label: "Work orders",
		can: (s) => s.canReadWorkOrders,
		words: ["work order", "work orders", "swo"],
		rows: (s) => s.workOrders,
		date: (r) => r.date,
		amount: (r) => n(r.total_value),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			subcontractor: { label: "Subcontractor", get: (r) => r.subcontractor_name || r.subcontractor || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.date) },
		},
		list: {
			columns: [
				{ key: "name", label: "WO" },
				{ key: "subcontractor", label: "Subcontractor" },
				{ key: "project", label: "Project" },
				{ key: "value", label: "Value", align: "right", money: true },
			],
			row: (r, s) => ({
				name: r.name,
				subcontractor: r.subcontractor_name || r.subcontractor || "—",
				project: pName(s, r.project),
				value: n(r.total_value),
			}),
		},
	},
	measurementBooks: {
		label: "Measurement books",
		can: (s) => s.canReadMeasurementBooks,
		words: ["measurement book", "measurement books", "mb", "measurement"],
		rows: (s) => s.measurementBooks,
		date: (r) => r.date,
		amount: () => 0,
		qty: (r) => n(r.measured_total),
		project: (r) => r.project,
		measures: ["count", "qty"],
		dims: {
			status: { label: "Status", get: (r) => r.status || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.date) },
		},
		list: {
			columns: [
				{ key: "name", label: "MB" },
				{ key: "project", label: "Project" },
				{ key: "date", label: "Date" },
				{ key: "status", label: "Status" },
			],
			row: (r, s) => ({
				name: r.name,
				project: pName(s, r.project),
				date: r.date || "—",
				status: r.status || "—",
			}),
		},
	},
	invoices: {
		label: "Invoices",
		can: (s) => s.canReadInvoices,
		words: ["invoice", "invoices", "billing", "revenue", "income", "sales", "receivable", "receivables"],
		rows: (s) => s.invoices,
		date: (r) => r.posting_date,
		amount: (r) => n(r.grand_total),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			customer: { label: "Customer", get: (r) => r.customer_name || r.customer || "—" },
			status: { label: "Status", get: (r) => r.status || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.posting_date) },
		},
		list: {
			columns: [
				{ key: "name", label: "Invoice" },
				{ key: "customer", label: "Customer" },
				{ key: "status", label: "Status" },
				{ key: "total", label: "Total", align: "right", money: true },
			],
			row: (r) => ({
				name: r.name,
				customer: r.customer_name || r.customer || "—",
				status: r.status || "—",
				total: n(r.grand_total),
			}),
		},
	},
	bills: {
		label: "Supplier bills",
		can: (s) => s.canReadBills,
		words: ["supplier bill", "supplier bills", "purchase invoice", "payable", "payables", "supplier spend"],
		rows: (s) => s.bills,
		date: (r) => r.posting_date,
		amount: (r) => n(r.grand_total),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			supplier: { label: "Supplier", get: (r) => r.supplier_name || r.supplier || "—" },
			status: { label: "Status", get: (r) => r.status || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.posting_date) },
		},
		list: {
			columns: [
				{ key: "name", label: "Bill" },
				{ key: "supplier", label: "Supplier" },
				{ key: "status", label: "Status" },
				{ key: "total", label: "Total", align: "right", money: true },
			],
			row: (r) => ({
				name: r.name,
				supplier: r.supplier_name || r.supplier || "—",
				status: r.status || "—",
				total: n(r.grand_total),
			}),
		},
	},
	expenses: {
		label: "Expenses",
		can: (s) => s.canReadExpenses,
		words: ["expense", "expenses", "spend", "spending", "overhead", "overheads"],
		rows: (s) => s.expenses,
		date: (r) => r.date,
		amount: (r) => n(r.amount),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			costType: { label: "Cost type", get: (r) => r.costType || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			employee: { label: "Paid by", get: (r) => r.employee || "—" },
			month: { label: "Month", get: (r) => monthOf(r.date) },
		},
		list: {
			columns: [
				{ key: "costType", label: "Cost type" },
				{ key: "project", label: "Project" },
				{ key: "date", label: "Date" },
				{ key: "amount", label: "Amount", align: "right", money: true },
			],
			row: (r, s) => ({
				costType: r.costType || "—",
				project: pName(s, r.project),
				date: r.date || "—",
				amount: n(r.amount),
			}),
		},
	},
	pettyCash: {
		label: "Petty cash",
		can: (s) => s.canReadPettyCash,
		words: ["petty cash", "float", "cash advance"],
		rows: (s) => s.pettyCash,
		date: (r) => r.request_date,
		amount: (r) => n(r.amount),
		qty: () => 0,
		project: (r) => r.project,
		measures: ["amount", "count"],
		dims: {
			status: { label: "Status", get: (r) => r.status || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			holder: { label: "Holder", get: (r) => r.requested_by || "—" },
			month: { label: "Month", get: (r) => monthOf(r.request_date) },
		},
		list: {
			columns: [
				{ key: "name", label: "Request" },
				{ key: "holder", label: "Holder" },
				{ key: "status", label: "Status" },
				{ key: "amount", label: "Amount", align: "right", money: true },
			],
			row: (r) => ({
				name: r.name,
				holder: r.requested_by || "—",
				status: r.status || "—",
				amount: n(r.amount),
			}),
		},
	},
	attendance: {
		label: "Labour attendance",
		can: (s) => s.canReadAttendance,
		words: ["attendance", "labour", "labor", "manpower", "man-days", "mandays", "workers", "wages"],
		rows: (s) => s.attendance,
		date: (r) => r.date,
		amount: () => 0,
		qty: () => 0,
		project: (r) => r.project,
		measures: ["mandays", "count"],
		dims: {
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			worker: { label: "Worker", get: (r) => r.employee || "—" },
			status: { label: "Status", get: (r) => r.status || "—" },
			month: { label: "Month", get: (r) => monthOf(r.date) },
		},
		list: {
			columns: [
				{ key: "date", label: "Date" },
				{ key: "worker", label: "Worker" },
				{ key: "status", label: "Status" },
				{ key: "project", label: "Project" },
			],
			row: (r, s) => ({
				date: r.date || "—",
				worker: r.employee || "—",
				status: r.status || "—",
				project: pName(s, r.project),
			}),
		},
	},
	receiptLines: {
		label: "Items received",
		can: (s) => s.canReadReceipts,
		words: ["purchase receipt", "purchase receipts", "goods receipt", "goods received", "items received", "received", "grn", "delivery", "deliveries"],
		rows: (s) => s.receiptLines,
		date: (r) => r.date,
		amount: (r) => n(r.amount),
		qty: (r) => n(r.receivedQty),
		project: (r) => r.project,
		measures: ["qty", "amount", "count"],
		dims: {
			item: { label: "Item", get: (r) => r.item_name || r.item || "—" },
			supplier: { label: "Supplier", get: (r) => r.supplier || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.date) },
		},
		list: {
			columns: [
				{ key: "date", label: "Date" },
				{ key: "item", label: "Item" },
				{ key: "qty", label: "Qty", align: "right" },
				{ key: "supplier", label: "Supplier" },
				{ key: "project", label: "Project" },
			],
			row: (r, s) => ({
				date: r.date || "—",
				item: r.item_name || r.item || "—",
				qty: n(r.receivedQty),
				supplier: r.supplier || "—",
				project: pName(s, r.project),
			}),
		},
	},
	consumptionLines: {
		label: "Material consumed",
		can: (s) => s.canReadConsumption,
		words: ["consumption", "consumed", "material used", "site use", "material consumption"],
		rows: (s) => s.consumptionLines,
		date: (r) => r.date,
		amount: () => 0,
		qty: (r) => n(r.qty),
		project: (r) => r.project,
		measures: ["qty", "count"],
		dims: {
			item: { label: "Item", get: (r) => r.item_name || r.item || "—" },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.date) },
		},
		list: {
			columns: [
				{ key: "date", label: "Date" },
				{ key: "item", label: "Item" },
				{ key: "qty", label: "Qty", align: "right" },
				{ key: "project", label: "Project" },
			],
			row: (r, s) => ({
				date: r.date || "—",
				item: r.item_name || r.item || "—",
				qty: n(r.qty),
				project: pName(s, r.project),
			}),
		},
	},
	items: {
		label: "Item master",
		can: (s) => s.canReadItems,
		words: ["item master", "items list", "item list", "catalogue", "catalog"],
		rows: (s) => s.items,
		date: () => null,
		amount: (r) => n(r.standard_rate),
		qty: () => 0,
		project: () => null,
		measures: ["count", "amount"],
		dims: {
			group: { label: "Item group", get: (r) => r.item_group || "—" },
			uom: { label: "UOM", get: (r) => r.stock_uom || "—" },
		},
		list: {
			columns: [
				{ key: "name", label: "Item" },
				{ key: "group", label: "Group" },
				{ key: "uom", label: "UOM" },
				{ key: "rate", label: "Rate", align: "right", money: true },
			],
			row: (r) => ({
				name: r.item_name || r.name,
				group: r.item_group || "—",
				uom: r.stock_uom || "—",
				rate: n(r.standard_rate),
			}),
		},
	},
	machineryUsage: {
		label: "Machinery usage",
		can: (s) => s.canReadMachineryUsage,
		words: ["machinery usage", "machinery", "equipment usage", "plant usage", "machine hours"],
		rows: (s) => s.machineryUsage,
		date: (r) => r.date,
		amount: (r) => n(r.quantity) * n(r.rate) + n(r.fuel_cost),
		qty: (r) => n(r.quantity),
		project: (r) => r.project,
		measures: ["amount", "qty", "count"],
		dims: {
			machine: { label: "Machine", get: (r, s) => s.machineryName(r.machine) },
			project: { label: "Project", get: (r, s) => pName(s, r.project) },
			month: { label: "Month", get: (r) => monthOf(r.date) },
		},
		list: {
			columns: [
				{ key: "date", label: "Date" },
				{ key: "machine", label: "Machine" },
				{ key: "hours", label: "Qty", align: "right" },
				{ key: "project", label: "Project" },
			],
			row: (r, s) => ({
				date: r.date || "—",
				machine: s.machineryName(r.machine),
				hours: n(r.quantity),
				project: pName(s, r.project),
			}),
		},
	},
	fieldEmployees: {
		label: "Field employees",
		can: (s) => s.canReadFieldEmployees,
		words: ["field employee", "field employees", "labour list", "worker list", "workers list"],
		rows: (s) => s.fieldEmployees,
		date: (r) => r.date_of_joining,
		amount: (r) => n(r.custom_wage),
		qty: () => 0,
		project: () => null,
		measures: ["count", "amount"],
		dims: {
			trade: { label: "Trade", get: (r) => r.custom_trade || "—" },
			contractor: { label: "Contractor", get: (r) => r.custom_contractor || "—" },
			status: { label: "Status", get: (r) => r.status || "—" },
		},
		list: {
			columns: [
				{ key: "name", label: "Employee" },
				{ key: "trade", label: "Trade" },
				{ key: "contractor", label: "Contractor" },
				{ key: "wage", label: "Daily wage", align: "right", money: true },
			],
			row: (r) => ({
				name: r.employee_name || r.name,
				trade: r.custom_trade || "—",
				contractor: r.custom_contractor || "—",
				wage: n(r.custom_wage),
			}),
		},
	},
};

export function availableDatasets(store) {
	return Object.entries(DATASETS).filter(([, ds]) => {
		try {
			return ds.can(store);
		} catch {
			return false;
		}
	});
}

export const MEASURE_LABEL = { count: "Count", amount: "Value", mandays: "Man-days", qty: "Quantity" };
export const VIZ = ["bar", "column", "line", "donut", "table", "kpi"];

// ---------------------------------------------------------------------------
// Parser — prompt → spec. Replaced by a model call in production. (verbatim)
// ---------------------------------------------------------------------------
const DIM_WORDS = {
	project: ["project", "projects", "site", "sites", "job"],
	status: ["status", "state"],
	state: ["approval", "approval state", "workflow", "state"],
	month: ["month", "monthly", "over time", "trend", "date", "timeline"],
	priority: ["priority"],
	supplier: ["supplier", "suppliers", "vendor", "vendors"],
	subcontractor: ["subcontractor", "subcontractors"],
	company: ["company"],
	type: ["type"],
	customer: ["customer", "customers", "client", "clients"],
	costType: ["cost type", "cost head", "account", "category"],
	item: ["item", "items", "material", "materials", "sku"],
	worker: ["worker", "workers", "employee", "employees"],
	holder: ["holder", "holders", "requested by"],
	machine: ["machine", "machines", "equipment", "plant"],
	trade: ["trade", "trades", "skill"],
	contractor: ["contractor", "contractors"],
	group: ["group", "item group"],
	uom: ["uom", "unit", "units"],
	blocker: ["blocker", "blockers", "blocked"],
};
const VIZ_WORDS = {
	donut: ["pie", "donut", "doughnut", "share", "split", "breakdown", "proportion"],
	line: ["line", "trend", "over time", "timeline"],
	column: ["column", "vertical bar"],
	bar: ["bar", "chart", "graph", "ranked"],
	table: ["table", "grid"],
	kpi: ["total", "how many", "how much", "number of", "sum"],
};
const MEASURE_WORDS = {
	amount: ["value", "amount", "cost", "spend", "spent", "worth", "rupees", "money"],
	mandays: ["man-days", "mandays", "man days", "manpower", "days worked"],
	qty: ["quantity", "qty", "volume", "hours", "how much of"],
	count: ["count", "how many", "number of", "no of"],
};
const LIST_WORDS = ["list", "show me the", "which ", "what were", "detail", "details", "log of", "register of", "itemised", "itemized", "line by line"];

function hit(text, words) {
	return words.some((w) => text.includes(w));
}

function editDistance(a, b) {
	if (Math.abs(a.length - b.length) > 2) return 99;
	const prev = Array.from({ length: b.length + 1 }, (_, j) => j);
	for (let i = 1; i <= a.length; i++) {
		let diag = prev[0];
		prev[0] = i;
		for (let j = 1; j <= b.length; j++) {
			const tmp = prev[j];
			prev[j] = Math.min(prev[j] + 1, prev[j - 1] + 1, diag + (a[i - 1] === b[j - 1] ? 0 : 1));
			diag = tmp;
		}
	}
	return prev[b.length];
}
function tolerance(w) {
	return w.length >= 6 ? 2 : w.length >= 5 ? 1 : 0;
}
function tokenMatches(token, word) {
	if (token === word) return true;
	const t = tolerance(word);
	return t > 0 && editDistance(token, word) <= t;
}
function fuzzyIncludes(tokens, phrase) {
	return phrase
		.split(" ")
		.filter(Boolean)
		.every((w) => tokens.some((tk) => tokenMatches(tk, w)));
}

export function parsePrompt(prompt, store, base = null) {
	const text = ` ${String(prompt || "").toLowerCase().trim()} `;
	if (!text.trim()) return null;
	const spec = base
		? JSON.parse(JSON.stringify(base))
		: { source: null, mode: "aggregate", measure: "count", dimension: null, filters: {}, viz: "bar", sort: "desc", limit: null };
	const understood = [];
	const allowed = availableDatasets(store);

	const forSource = text.replace(/\b(?:group by|split by|by)\s+[a-z\s-]{2,20}/g, " ");
	const tokens = forSource.split(/[^a-z0-9-]+/).filter(Boolean);
	let best = null;
	for (const [key, ds] of allowed) {
		for (const w of ds.words) {
			const exact = forSource.includes(w);
			const fuzzy = !exact && fuzzyIncludes(tokens, w);
			if (!exact && !fuzzy) continue;
			const score = w.length - (fuzzy ? 0.5 : 0);
			if (!best || score > best.len) best = { key, len: score, label: ds.label };
		}
	}
	if (!best) return null;
	spec.source = best.key;
	understood.push(best.label);

	const ds = DATASETS[spec.source];

	if (hit(text, LIST_WORDS)) {
		spec.mode = "list";
		understood.push("as a list");
	}

	let measured = false;
	for (const m of ["mandays", "qty", "amount", "count"]) {
		if (ds.measures.includes(m) && hit(text, MEASURE_WORDS[m])) {
			spec.measure = m;
			measured = true;
			understood.push(MEASURE_LABEL[m]);
			break;
		}
	}
	if (!measured || !ds.measures.includes(spec.measure)) spec.measure = ds.measures[0];

	const byMatch = text.match(/\bby ([a-z\s-]{2,20})/);
	let dim = null;
	if (byMatch) {
		const phrase = byMatch[1].trim();
		for (const k of Object.keys(ds.dims)) {
			if ((DIM_WORDS[k] || []).some((w) => phrase.startsWith(w))) {
				dim = k;
				break;
			}
		}
	}
	if (!dim) {
		for (const k of Object.keys(ds.dims)) {
			if ((DIM_WORDS[k] || []).some((w) => text.includes(` ${w} `))) {
				dim = k;
				break;
			}
		}
	}
	if (dim) {
		spec.dimension = dim;
		understood.push(`by ${ds.dims[dim].label}`);
	}
	if (!spec.dimension || !ds.dims[spec.dimension]) spec.dimension = Object.keys(ds.dims)[0];

	for (const [v, words] of Object.entries(VIZ_WORDS)) {
		if (v === "kpi" && dim) continue;
		if (hit(text, words)) {
			spec.viz = v;
			understood.push(v);
			break;
		}
	}
	if (spec.dimension === "month" && spec.viz === "bar") spec.viz = "line";

	for (const p of store.projects) {
		const code = (p.code || "").toLowerCase();
		const words = (p.name || "").toLowerCase().split(/\s+/).filter((w) => w.length > 2);
		const opener = words.slice(0, 2).join(" ");
		if ((code.length > 2 && text.includes(code)) || (opener.length > 4 && text.includes(opener))) {
			spec.filters.project = p.id;
			understood.push(p.name);
			break;
		}
	}

	const now = new Date();
	const iso = (d) => d.toISOString().slice(0, 10);
	const back = (days) => iso(new Date(now.getTime() - days * 86400000));
	if (text.includes("today")) {
		spec.filters.from = iso(now);
		understood.push("today");
	} else if (text.includes("last 7") || text.includes("this week") || text.includes("past week")) {
		spec.filters.from = back(7);
		understood.push("last 7 days");
	} else if (text.includes("last month") || text.includes("last 30") || text.includes("this month") || text.includes("past month")) {
		spec.filters.from = back(30);
		understood.push("last 30 days");
	} else if (text.includes("last 90") || text.includes("quarter")) {
		spec.filters.from = back(90);
		understood.push("last 90 days");
	} else if (text.includes("this year") || text.includes("ytd")) {
		spec.filters.from = `${now.getFullYear()}-01-01`;
		understood.push("year to date");
	}

	const topMatch = text.match(/\btop (\d{1,2})/);
	if (topMatch) {
		spec.limit = Number(topMatch[1]);
		understood.push(`top ${spec.limit}`);
	}
	if (text.includes("ascending") || text.includes("lowest") || text.includes("smallest")) spec.sort = "asc";
	if (text.includes("descending") || text.includes("highest") || text.includes("largest")) spec.sort = "desc";
	if (text.includes("alphabetical") || text.includes("a-z")) spec.sort = "label";

	applyValueFilters(spec, text, store, understood);

	spec.understood = understood;
	return spec;
}

function applyValueFilters(spec, text, store, understood) {
	spec.filters.values = spec.filters.values || {};
	const num = (raw) => {
		const v = Number(String(raw).replace(/[,]/g, ""));
		if (!Number.isFinite(v)) return null;
		if (/\blakh|\bl\b/.test(text) && v < 1000) return v * 100000;
		if (/\bcrore|\bcr\b/.test(text) && v < 1000) return v * 10000000;
		return v;
	};
	const over = text.match(/\b(?:over|above|more than|greater than|exceeding)\s+₹?\s*([\d,]+)/);
	if (over) {
		const v = num(over[1]);
		if (v != null) {
			spec.filters.min = v;
			understood.push(`over ${over[1]}`);
		}
	}
	const under = text.match(/\b(?:under|below|less than|up to)\s+₹?\s*([\d,]+)/);
	if (under) {
		const v = num(under[1]);
		if (v != null) {
			spec.filters.max = v;
			understood.push(`under ${under[1]}`);
		}
	}

	const dv = dimensionValues(spec.source, store);
	let bestVal = null;
	for (const [k, d] of Object.entries(dv)) {
		for (const v of d.values) {
			const lv = v.toLowerCase();
			if (lv.length < 4) continue;
			if (text.includes(lv) && (!bestVal || lv.length > bestVal.len)) bestVal = { k, v, len: lv.length, label: d.label };
		}
	}
	if (bestVal && !(bestVal.k === "project" && spec.filters.project)) {
		spec.filters.values[bestVal.k] = bestVal.v;
		understood.push(`${bestVal.label} = ${bestVal.v}`);
	}
	if (!Object.keys(spec.filters.values).length) delete spec.filters.values;
}

export function refineSpec(spec, prompt) {
	const text = ` ${String(prompt || "").toLowerCase().trim()} `;
	const next = JSON.parse(JSON.stringify(spec));
	const applied = [];
	const ds = DATASETS[next.source];

	if (hit(text, LIST_WORDS)) {
		next.mode = "list";
		applied.push("as a list");
	}
	if (text.includes("summar") || text.includes("roll up") || text.includes("rollup") || text.includes("group it")) {
		next.mode = "aggregate";
		applied.push("summarised");
	}
	for (const [v, words] of Object.entries(VIZ_WORDS)) {
		if (hit(text, words)) {
			next.viz = v;
			next.mode = "aggregate";
			applied.push(`shown as ${v}`);
			break;
		}
	}
	const byMatch = text.match(/\b(?:by|group by|split by) ([a-z\s-]{2,20})/);
	if (byMatch) {
		const phrase = byMatch[1].trim();
		for (const k of Object.keys(ds.dims)) {
			if ((DIM_WORDS[k] || []).some((w) => phrase.startsWith(w))) {
				next.dimension = k;
				next.mode = "aggregate";
				applied.push(`grouped by ${ds.dims[k].label}`);
				break;
			}
		}
	}
	for (const m of ["mandays", "qty", "amount", "count"]) {
		if (ds.measures.includes(m) && hit(text, MEASURE_WORDS[m])) {
			next.measure = m;
			applied.push(MEASURE_LABEL[m]);
			break;
		}
	}
	const topMatch = text.match(/\btop (\d{1,2})/);
	if (topMatch) {
		next.limit = Number(topMatch[1]);
		applied.push(`top ${next.limit}`);
	}
	if (text.includes("show all") || text.includes("all rows") || text.includes("remove limit")) {
		next.limit = null;
		applied.push("all rows");
	}
	if (text.includes("ascending") || text.includes("lowest")) {
		next.sort = "asc";
		applied.push("ascending");
	}
	if (text.includes("descending") || text.includes("highest")) {
		next.sort = "desc";
		applied.push("descending");
	}
	if (text.includes("alphabetical") || text.includes("a-z")) {
		next.sort = "label";
		applied.push("alphabetical");
	}
	if (text.includes("all projects") || text.includes("every project")) {
		delete next.filters.project;
		applied.push("all projects");
	}
	if (text.includes("all time") || text.includes("no date") || text.includes("remove date")) {
		delete next.filters.from;
		delete next.filters.to;
		applied.push("all dates");
	}
	if (text.includes("clear filter") || text.includes("remove filter") || text.includes("no filter")) {
		next.filters = {};
		applied.push("filters cleared");
	}

	if (!applied.length) return null;
	next.understood = applied;
	return next;
}

export function refineWithStore(spec, prompt, store) {
	const text = ` ${String(prompt || "").toLowerCase().trim()} `;
	const base = refineSpec(spec, prompt);
	const next = base || JSON.parse(JSON.stringify(spec));
	const applied = base ? [...(base.understood || [])] : [];
	const before = JSON.stringify(next.filters);
	applyValueFilters(next, text, store, applied);
	if (!base && JSON.stringify(next.filters) === before) return null;
	next.understood = applied;
	return next;
}

// ---------------------------------------------------------------------------
// Executor — spec → result, straight off the live rows. (verbatim)
// ---------------------------------------------------------------------------
export function filteredRows(spec, store) {
	const ds = DATASETS[spec.source];
	if (!ds || !ds.can(store)) return [];
	const f = spec.filters || {};

	const scope = f.project
		? new Set([f.project, ...store.projects.filter((p) => p.parentId === f.project).map((p) => p.id)])
		: null;
	const q = (f.q || "").trim().toLowerCase();
	const values = f.values || {};
	const dimEntries = Object.entries(values).filter(([, v]) => v);

	return ds.rows(store).filter((r) => {
		if (scope) {
			const pid = ds.project(r, store);
			if (!pid || !scope.has(pid)) return false;
		}
		const d = ds.date(r);
		if (f.from && (!d || d < f.from)) return false;
		if (f.to && (!d || d > f.to)) return false;
		if (f.min != null || f.max != null) {
			const v = measureOf(ds, r, spec.measure);
			if (f.min != null && v < f.min) return false;
			if (f.max != null && v > f.max) return false;
		}
		for (const [k, want] of dimEntries) {
			const dim = ds.dims[k];
			if (dim && String(dim.get(r, store)) !== String(want)) return false;
		}
		if (q) {
			const hay = Object.values(ds.list.row(r, store)).join(" ").toLowerCase();
			if (!hay.includes(q)) return false;
		}
		return true;
	});
}

export function dimensionValues(source, store, cap = 60) {
	const ds = DATASETS[source];
	if (!ds || !ds.can(store)) return {};
	const rows = ds.rows(store);
	const out = {};
	for (const [k, dim] of Object.entries(ds.dims)) {
		const set = new Set();
		for (const r of rows) {
			const v = dim.get(r, store);
			if (v && v !== "—") set.add(String(v));
			if (set.size > cap) break;
		}
		out[k] = { label: dim.label, values: [...set].sort((a, b) => a.localeCompare(b)) };
	}
	return out;
}

export function runSpec(spec, store, window = null) {
	const ds = DATASETS[spec.source];
	if (!ds || !ds.can(store)) return null;

	const rows = filteredRows(spec, store);
	const base = {
		recordCount: rows.length,
		datasetLabel: ds.label,
		measure: spec.measure,
		measureLabel: MEASURE_LABEL[spec.measure],
	};

	if (spec.mode === "list") {
		const dateOf = (r) => ds.date(r) || "";
		const sorted = rows.slice().sort((a, b) => String(dateOf(b)).localeCompare(String(dateOf(a))));
		const offset = Math.max(0, window?.offset || 0);
		const size = window?.pageSize || sorted.length;
		const page = sorted.slice(offset, offset + size);
		return {
			...base,
			mode: "list",
			columns: ds.list.columns,
			records: page.map((r, i) => ({ _k: r._key || r.name || `${offset + i}`, ...ds.list.row(r, store) })),
			offset,
			pageSize: size,
			total: +rows.reduce((a, r) => a + measureOf(ds, r, spec.measure), 0).toFixed(2),
			truncated: 0,
			dimensionLabel: "",
		};
	}

	const dim = ds.dims[spec.dimension] || Object.values(ds.dims)[0];
	const buckets = new Map();
	for (const r of rows) {
		const key = dim.get(r, store) || "—";
		buckets.set(key, (buckets.get(key) || 0) + measureOf(ds, r, spec.measure));
	}

	let out = [...buckets.entries()].map(([label, value]) => ({ label, value: +value.toFixed(2) }));
	if (spec.dimension === "month") out.sort((a, b) => monthKey(a.label) - monthKey(b.label));
	else if (spec.sort === "label") out.sort((a, b) => a.label.localeCompare(b.label));
	else if (spec.sort === "asc") out.sort((a, b) => a.value - b.value);
	else out.sort((a, b) => b.value - a.value);

	let truncated = 0;
	if (spec.limit && out.length > spec.limit) {
		truncated = out.length - spec.limit;
		out = out.slice(0, spec.limit);
	}

	return {
		...base,
		mode: "aggregate",
		rows: out,
		total: +out.reduce((a, r) => a + r.value, 0).toFixed(2),
		truncated,
		dimensionLabel: dim.label,
	};
}

function measureOf(ds, r, measure) {
	if (measure === "amount") return ds.amount(r);
	if (measure === "qty") return ds.qty(r);
	if (measure === "mandays") return r.status === "Half Day" ? 0.5 : r.status === "Absent" ? 0 : 1;
	return 1;
}

function monthKey(label) {
	if (!label || label === "—") return 0;
	const [m, y] = label.split(" ");
	return Number(y) * 12 + MONTHS.indexOf(m);
}

export function describeSpec(spec) {
	const ds = DATASETS[spec.source];
	if (!ds) return "";
	if (spec.mode === "list") return `${ds.label} — detail`;
	const dim = ds.dims[spec.dimension];
	const bits = [`${MEASURE_LABEL[spec.measure]} of ${ds.label.toLowerCase()}`];
	if (dim) bits.push(`by ${dim.label.toLowerCase()}`);
	return bits.join(" ");
}

// ---------------------------------------------------------------------------
// Presets + suggestions — Core-5 cut. A preset is the same spec shape, so it is
// refinable like anything else.
// ---------------------------------------------------------------------------
const P = (source, measure, dimension, viz, extra = {}) => ({
	source,
	mode: "aggregate",
	measure,
	dimension,
	filters: {},
	viz,
	sort: "desc",
	limit: null,
	...extra,
});

export const ALL_PRESETS = [
	{ id: "spend-by-supplier", title: "Spend by supplier", prompt: "supplier bill value by supplier, top 8", spec: P("bills", "amount", "supplier", "bar", { limit: 8 }) },
	{ id: "revenue-by-month", title: "Revenue by month", prompt: "invoice value by month", spec: P("invoices", "amount", "month", "line") },
	{ id: "tasks-by-status", title: "Tasks by status", prompt: "tasks by status as a pie", spec: P("tasks", "count", "status", "donut") },
	{ id: "cost-by-type", title: "Expenses by cost type", prompt: "expense value by cost type", spec: P("expenses", "amount", "costType", "donut") },
	{ id: "manpower", title: "Man-days by project", prompt: "man-days by project", spec: P("attendance", "mandays", "project", "bar") },
	{ id: "sub-billing", title: "Subcontractor billing", prompt: "subcontractor bill value by subcontractor", spec: P("subBills", "amount", "subcontractor", "bar") },
	{ id: "received-by-item", title: "Material received", prompt: "items received by item", spec: P("receiptLines", "qty", "item", "bar") },
	{ id: "received-detail", title: "Deliveries — detail", prompt: "list items received last month", spec: P("receiptLines", "qty", "item", "table", { mode: "list" }) },
	{ id: "consumed-by-item", title: "Material consumed", prompt: "consumption by item", spec: P("consumptionLines", "qty", "item", "bar") },
	{ id: "po-by-status", title: "POs by status", prompt: "purchase order value by status", spec: P("purchaseOrders", "amount", "status", "bar") },
	{ id: "reporting", title: "Site reporting by month", prompt: "progress entries by month", spec: P("progress", "count", "month", "line") },
	{ id: "variations", title: "Scope changes", prompt: "scope change value by status", spec: P("scos", "amount", "status", "bar") },
];

export function availablePresets(store) {
	return ALL_PRESETS.filter((p) => DATASETS[p.spec.source]?.can(store));
}

export const SUGGESTIONS = [
	"List items received last month",
	"Supplier spend by supplier, top 5",
	"Invoice value by month",
	"Tasks by status as a pie",
	"Man-days by project this month",
	"Material consumed by item",
];
