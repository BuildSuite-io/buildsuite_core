import { createRouter, createWebHistory } from "vue-router";
import { useSessionStore } from "@/stores/session";
import { getLoginUrl } from "@/utils/session";
import { APP_ROUTE, APP_TITLE } from "@/utils/appRoute";

// Per-route browser title (route name -> human label). Detail pages get a generic
// label here; the view overrides it with the record name via usePageTitle.
const PAGE_TITLES = {
	"app-home": "Home",
	dashboard: "Dashboard",
	projects: "Projects",
	"project-new": "New Project",
	"project-detail": "Project",
	"project-progress-report": "Progress Report",
	"work-packages": "Work Packages",
	"wp-new": "New Work Package",
	"wp-detail": "Work Package",
	tasks: "Tasks",
	"task-new": "New Task",
	"task-detail": "Task",
	"stage-plannings": "Stage Planning",
	"stage-planning-new": "New Stage",
	"stage-planning-detail": "Stage Planning",
	"stage-planning-review": "Stage Review",
	"progress-entries": "Task Progress Entries",
	"progress-entry-new": "New Progress Entry",
	"progress-entry-detail": "Task Progress Entry",
	schedule: "Schedule",
	sco: "Scope Change Orders",
	"sco-new": "Raise Scope Change Order",
	"sco-detail": "Scope Change Order",
	boq: "Bill of Quantities",
	"boq-detail": "BOQ",
	"rate-master": "Rate Master",
	"rate-master-detail": "Rate Master",
	assembly: "Assemblies",
	"assembly-new": "New Assembly",
	"assembly-detail": "Assembly",
	"site-execution": "Site Execution",
	"project-dashboard": "Project Dashboard",
	"report-stub": "Report",
	"report-delay-analysis": "Delay Analysis",
	estimation: "Estimation",
	procurement: "Procurement",
	"procurement-dashboard": "Procurement Dashboard",
	items: "Items",
	"material-consumption": "Material Consumption",
	"material-consumption-new": "Record Consumption",
	"material-consumption-detail": "Material Consumption",
	"material-consumption-edit": "Edit Consumption",
	equipment: "Equipment",
	"equipment-dashboard": "Equipment Dashboard",
	machinery: "Machinery",
	"machinery-new": "New Machinery",
	"machinery-detail": "Machinery",
	"machinery-usage": "Machinery Usage",
	"machinery-usage-new": "Log Machinery Usage",
	"machinery-usage-detail": "Machinery Usage",
	subcontract: "Subcontract",
	"subcontract-dashboard": "Subcontractor Dashboard",
	subcontractors: "Subcontractors",
	"subcontractor-new": "New Subcontractor",
	"subcontractor-detail": "Subcontractor",
	"subcontractor-work-orders": "Work Orders",
	"subcontractor-work-order-new": "New Work Order",
	"subcontractor-work-order-detail": "Work Order",
	"subcontractor-work-order-edit": "Edit Work Order",
	"measurement-books": "Measurement Books",
	"measurement-book-new": "New Measurement Book",
	"measurement-book-detail": "Measurement Book",
	"measurement-book-edit": "Edit Measurement Book",
	"subcontractor-bills": "Subcontractor Bills",
	"subcontractor-bill-new": "New Subcontractor Bill",
	"subcontractor-bill-detail": "Subcontractor Bill",
	"subcontractor-bill-edit": "Edit Subcontractor Bill",
	workforce: "Workforce",
	"field-employees": "Field Employees",
	"field-employee-new": "New Field Employee",
	"field-employee-detail": "Field Employee",
	crews: "Crews",
	"crew-new": "New Crew",
	"crew-detail": "Crew",
	"field-attendance": "Field Attendance",
	"field-attendance-new": "New Field Attendance",
	"field-attendance-detail": "Field Attendance",
	"labour-attendance": "Labour Attendance Register",
	"overtime-attendance": "Overtime Attendance Register",
	"scope-change": "Scope Change",
	"project-finance": "Project Finance",
	"petty-cash": "Petty Cash",
	accounting: "Accounting",
	buying: "Buying",
	stock: "Stock",
	assets: "Assets",
	hr: "HR",
	subcontractor: "Subcontractor",
	labour: "Labour",
	financials: "Financials",
	reports: "Reports",
	settings: "Settings",
	"settings-companies": "Companies",
	"settings-company-new": "New Company",
	"settings-company-detail": "Company",
	"settings-users": "Users",
	"settings-user-new": "New User",
	"settings-data": "Data Tools",
	"settings-core": "Core Settings",
	"settings-workspaces": "Workspace Setting",
	"settings-workspace-structure": "Workspace Structure",
	"settings-project-categories": "Project Categories",
	"settings-project-category-new": "New Project Category",
	"settings-project-category-detail": "Project Category",
	"settings-project-category-template": "Project Template",
	"settings-personas": "Personas",
	"settings-persona-new": "New Persona",
	"settings-persona-detail": "Persona",
	forbidden: "Access Denied",
};

const routes = [
	{
		path: "/",
		component: () => import("@/layouts/DeskShell.vue"),
		children: [
			{ path: "", redirect: "/home" },
			{ path: "home", name: "app-home", component: () => import("@/views/AppHomeView.vue") },
			{
				path: "dashboard",
				name: "dashboard",
				component: () => import("@/views/DashboardView.vue"),
			},
			{
				path: "projects",
				name: "projects",
				component: () => import("@/views/ProjectsView.vue"),
			},
			{
				path: "projects/new",
				name: "project-new",
				component: () => import("@/views/NewProjectView.vue"),
			},
			{
				path: "projects/:id",
				name: "project-detail",
				component: () => import("@/views/ProjectDetailView.vue"),
				props: true,
			},
			{
				path: "projects/:id/progress-report",
				name: "project-progress-report",
				component: () => import("@/views/ProgressReportView.vue"),
				props: true,
			},
			{
				path: "work-packages",
				name: "work-packages",
				component: () => import("@/views/WorkPackagesView.vue"),
			},
			{
				path: "work-packages/new",
				name: "wp-new",
				component: () => import("@/views/NewWorkPackageView.vue"),
			},
			{
				path: "work-packages/:id",
				name: "wp-detail",
				component: () => import("@/views/WorkPackageDetailView.vue"),
				props: true,
			},
			{ path: "tasks", name: "tasks", component: () => import("@/views/TasksView.vue") },
			{
				path: "tasks/new",
				name: "task-new",
				component: () => import("@/views/NewTaskView.vue"),
			},
			{
				path: "tasks/:id",
				name: "task-detail",
				component: () => import("@/views/TaskDetailView.vue"),
				props: true,
			},
			{
				path: "stage-plannings",
				name: "stage-plannings",
				component: () => import("@/views/StagePlanningsView.vue"),
			},
			{
				path: "stage-plannings/new",
				name: "stage-planning-new",
				component: () => import("@/views/NewStagePlanningView.vue"),
			},
			{
				path: "stage-plannings/:id",
				name: "stage-planning-detail",
				component: () => import("@/views/StagePlanningDetailView.vue"),
				props: true,
			},
			{
				path: "stage-plannings/:id/review",
				name: "stage-planning-review",
				component: () => import("@/views/StageReviewView.vue"),
				props: true,
			},
			{
				path: "progress-entries",
				name: "progress-entries",
				component: () => import("@/views/TaskProgressEntriesView.vue"),
			},
			{
				path: "progress-entries/new",
				name: "progress-entry-new",
				component: () => import("@/views/NewTaskProgressEntryView.vue"),
			},
			{
				path: "progress-entries/:id",
				name: "progress-entry-detail",
				component: () => import("@/views/TaskProgressEntryDetailView.vue"),
				props: true,
			},
			{
				path: "schedule",
				name: "schedule",
				component: () => import("@/views/ScheduleView.vue"),
			},
			{ path: "sco", name: "sco", component: () => import("@/views/ScoView.vue") },
			{
				path: "sco/new",
				name: "sco-new",
				component: () => import("@/views/NewScoView.vue"),
			},
			{
				path: "sco/:id",
				name: "sco-detail",
				component: () => import("@/views/ScoDetailView.vue"),
				props: true,
			},
			{ path: "boq", name: "boq", component: () => import("@/views/BoqView.vue") },
			{
				path: "boq/:id",
				name: "boq-detail",
				component: () => import("@/views/BoqDetailView.vue"),
				props: true,
			},
			{
				path: "rate-master",
				name: "rate-master",
				component: () => import("@/views/RateMasterView.vue"),
			},
			{
				path: "rate-master/:id",
				name: "rate-master-detail",
				component: () => import("@/views/RateMasterView.vue"),
				props: true,
			},
			{
				path: "assembly",
				name: "assembly",
				component: () => import("@/views/AssembliesView.vue"),
			},
			{
				path: "assembly/new",
				name: "assembly-new",
				component: () => import("@/views/NewAssemblyView.vue"),
			},
			{
				path: "assembly/:id",
				name: "assembly-detail",
				component: () => import("@/views/AssemblyDetailView.vue"),
				props: true,
			},
			{
				path: "estimate-template",
				name: "estimate-template",
				component: () => import("@/views/EstimateTemplatesView.vue"),
			},
			{
				path: "estimate-template/new",
				name: "estimate-template-new",
				component: () => import("@/views/NewEstimateTemplateView.vue"),
			},
			{
				path: "estimate-template/:id",
				name: "estimate-template-detail",
				component: () => import("@/views/EstimateTemplateDetailView.vue"),
				props: true,
			},

			{
				path: "site-execution",
				name: "site-execution",
				component: () => import("@/views/workspaces/SiteExecutionWorkspace.vue"),
			},
			{
				path: "project-dashboard",
				name: "project-dashboard",
				component: () => import("@/views/workspaces/ProjectDashboardView.vue"),
			},
			{
				// Insights — ask-a-question reporting. Leadership-gated in the view.
				path: "insights",
				name: "insights",
				component: () => import("@/views/InsightsView.vue"),
			},
			{
				path: "reports/view/:report",
				name: "report-view",
				component: () => import("@/views/ReportView.vue"),
				props: true,
			},
			{
				// Bespoke Site Execution report — its own route so the Workspace Setting tile
				// points at a plain URL rather than a Query Report the flat renderer can't express.
				path: "reports/delay-analysis",
				name: "report-delay-analysis",
				component: () => import("@/views/DelayAnalysisReportView.vue"),
			},
			{
				// Bespoke project cost-control report — Planned/Committed/Actual/Variance per BOQ
				// cost code. Launched from the project overview with ?project=<id>.
				path: "reports/cost-vs-budget",
				name: "report-cost-vs-budget",
				component: () => import("@/views/CostVsBudgetReportView.vue"),
			},
			{
				path: "reports/:slug",
				name: "report-stub",
				component: () => import("@/views/workspaces/ReportStubView.vue"),
				props: true,
			},
			{
				path: "estimation",
				name: "estimation",
				component: () => import("@/views/workspaces/EstimationWorkspace.vue"),
			},
			{
				path: "procurement",
				name: "procurement",
				component: () => import("@/views/workspaces/ProcurementWorkspace.vue"),
			},
			{
				path: "procurement-dashboard",
				name: "procurement-dashboard",
				component: () => import("@/views/workspaces/ProcurementDashboardView.vue"),
			},
			{
				path: "procurement/material-requests",
				name: "material-requests",
				component: () => import("@/views/procurement/MaterialRequestsListView.vue"),
			},
			{
				path: "procurement/material-requests/new",
				name: "material-request-new",
				component: () => import("@/views/procurement/NewMaterialRequestView.vue"),
			},
			{
				path: "procurement/material-requests/:id",
				name: "material-request-detail",
				component: () => import("@/views/procurement/MaterialRequestDetailView.vue"),
				props: true,
			},
			{
				path: "procurement/material-requests/:id/edit",
				name: "material-request-edit",
				component: () => import("@/views/procurement/NewMaterialRequestView.vue"),
			},
			{
				path: "records/:doctype/new",
				name: "record-new",
				component: () => import("@/views/records/DocTypeRecordFormView.vue"),
				props: true,
			},
			{
				path: "records/:doctype/:name",
				name: "record-edit",
				component: () => import("@/views/records/DocTypeRecordFormView.vue"),
				props: true,
			},
			{
				path: "records/:doctype",
				name: "records-list",
				component: () => import("@/views/records/DocTypeRecordsListView.vue"),
				props: true,
			},
			{
				path: "procurement/purchase-orders",
				name: "purchase-orders",
				component: () => import("@/views/procurement/PurchaseOrdersListView.vue"),
			},
			{
				path: "procurement/purchase-orders/new",
				name: "purchase-order-new",
				component: () => import("@/views/procurement/NewPurchaseOrderView.vue"),
			},
			{
				path: "procurement/purchase-orders/:id",
				name: "purchase-order-detail",
				component: () => import("@/views/procurement/PurchaseOrderDetailView.vue"),
				props: true,
			},
			{
				path: "procurement/purchase-orders/:id/edit",
				name: "purchase-order-edit",
				component: () => import("@/views/procurement/NewPurchaseOrderView.vue"),
			},
			{
				path: "procurement/purchase-orders/:id/print",
				name: "purchase-order-print",
				component: () => import("@/views/procurement/PurchaseOrderPrintView.vue"),
				props: true,
			},
			{
				path: "procurement/receipts",
				name: "purchase-receipts",
				component: () => import("@/views/procurement/PurchaseReceiptsListView.vue"),
			},
			{
				path: "procurement/receipts/new",
				name: "purchase-receipt-new",
				component: () => import("@/views/procurement/NewPurchaseReceiptView.vue"),
			},
			{
				path: "procurement/receipts/:id",
				name: "purchase-receipt-detail",
				component: () => import("@/views/procurement/PurchaseReceiptDetailView.vue"),
				props: true,
			},
			{
				path: "procurement/receipts/:id/edit",
				name: "purchase-receipt-edit",
				component: () => import("@/views/procurement/NewPurchaseReceiptView.vue"),
			},
			{
				path: "items",
				name: "items",
				component: () => import("@/views/ItemsListView.vue"),
			},
			{
				path: "material-consumption",
				name: "material-consumption",
				component: () => import("@/views/ConsumptionListView.vue"),
			},
			// `new` must stay above `:id`, or it is read as a record id.
			{
				path: "material-consumption/new",
				name: "material-consumption-new",
				component: () => import("@/views/NewConsumptionView.vue"),
			},
			{
				path: "material-consumption/:id/edit",
				name: "material-consumption-edit",
				component: () => import("@/views/NewConsumptionView.vue"),
				props: true,
			},
			{
				path: "material-consumption/:id",
				name: "material-consumption-detail",
				component: () => import("@/views/ConsumptionDetailView.vue"),
				props: true,
			},
			{
				path: "equipment",
				name: "equipment",
				component: () => import("@/views/workspaces/EquipmentWorkspace.vue"),
			},
			{
				path: "equipment-dashboard",
				name: "equipment-dashboard",
				component: () => import("@/views/workspaces/EquipmentDashboardView.vue"),
			},
			{
				path: "machinery",
				name: "machinery",
				component: () => import("@/views/MachineryListView.vue"),
			},
			{
				path: "machinery/new",
				name: "machinery-new",
				component: () => import("@/views/NewMachineryView.vue"),
			},
			{
				path: "machinery/:id",
				name: "machinery-detail",
				component: () => import("@/views/MachineryDetailView.vue"),
				props: true,
			},
			{
				path: "machinery-usage",
				name: "machinery-usage",
				component: () => import("@/views/MachineryUsageListView.vue"),
			},
			{
				path: "machinery-usage/new",
				name: "machinery-usage-new",
				component: () => import("@/views/NewMachineryUsageView.vue"),
			},
			{
				path: "machinery-usage/:id",
				name: "machinery-usage-detail",
				component: () => import("@/views/MachineryUsageDetailView.vue"),
				props: true,
			},
			{
				path: "subcontract",
				name: "subcontract",
				component: () => import("@/views/workspaces/SubcontractWorkspace.vue"),
			},
			{
				path: "subcontract-dashboard",
				name: "subcontract-dashboard",
				component: () => import("@/views/workspaces/SubcontractorDashboardView.vue"),
			},
			{
				path: "subcontractors",
				name: "subcontractors",
				component: () => import("@/views/SubcontractorsListView.vue"),
			},
			{
				path: "subcontractors/new",
				name: "subcontractor-new",
				component: () => import("@/views/NewSubcontractorView.vue"),
			},
			{
				path: "subcontractors/:id",
				name: "subcontractor-detail",
				component: () => import("@/views/SubcontractorDetailView.vue"),
				props: true,
			},
			{
				path: "subcontractor-work-orders",
				name: "subcontractor-work-orders",
				component: () => import("@/views/SubcontractorWorkOrdersListView.vue"),
			},
			{
				path: "subcontractor-work-orders/new",
				name: "subcontractor-work-order-new",
				component: () => import("@/views/NewSubcontractorWorkOrderView.vue"),
			},
			{
				path: "subcontractor-work-orders/:id",
				name: "subcontractor-work-order-detail",
				component: () => import("@/views/SubcontractorWorkOrderDetailView.vue"),
				props: true,
			},
			{
				path: "subcontractor-work-orders/:id/edit",
				name: "subcontractor-work-order-edit",
				component: () => import("@/views/NewSubcontractorWorkOrderView.vue"),
				props: true,
			},
			{
				path: "subcontractor-work-orders/:id/print",
				name: "subcontractor-work-order-print",
				component: () => import("@/views/SubcontractorWorkOrderPrintView.vue"),
				props: true,
			},
			{
				path: "measurement-books",
				name: "measurement-books",
				component: () => import("@/views/MeasurementBooksListView.vue"),
			},
			{
				path: "measurement-books/new",
				name: "measurement-book-new",
				component: () => import("@/views/NewMeasurementBookView.vue"),
			},
			{
				path: "measurement-books/:id",
				name: "measurement-book-detail",
				component: () => import("@/views/MeasurementBookDetailView.vue"),
				props: true,
			},
			{
				path: "measurement-books/:id/edit",
				name: "measurement-book-edit",
				component: () => import("@/views/NewMeasurementBookView.vue"),
				props: true,
			},
			{
				path: "subcontractor-bills",
				name: "subcontractor-bills",
				component: () => import("@/views/SubcontractorBillsListView.vue"),
			},
			{
				path: "subcontractor-bills/new",
				name: "subcontractor-bill-new",
				component: () => import("@/views/NewSubcontractorBillView.vue"),
			},
			{
				path: "subcontractor-bills/:id",
				name: "subcontractor-bill-detail",
				component: () => import("@/views/SubcontractorBillDetailView.vue"),
				props: true,
			},
			{
				path: "subcontractor-bills/:id/edit",
				name: "subcontractor-bill-edit",
				component: () => import("@/views/NewSubcontractorBillView.vue"),
				props: true,
			},
			{
				path: "workforce",
				name: "workforce",
				component: () => import("@/views/workspaces/WorkforceWorkspace.vue"),
			},
			{
				path: "field-employees",
				name: "field-employees",
				component: () => import("@/views/FieldEmployeesListView.vue"),
			},
			{
				path: "field-employees/new",
				name: "field-employee-new",
				component: () => import("@/views/NewFieldEmployeeView.vue"),
			},
			{
				path: "field-employees/:id",
				name: "field-employee-detail",
				component: () => import("@/views/FieldEmployeeDetailView.vue"),
				props: true,
			},
			{
				path: "crews",
				name: "crews",
				component: () => import("@/views/CrewsListView.vue"),
			},
			{
				path: "crews/new",
				name: "crew-new",
				component: () => import("@/views/NewCrewView.vue"),
			},
			{
				path: "crews/:id",
				name: "crew-detail",
				component: () => import("@/views/CrewDetailView.vue"),
				props: true,
			},
			{
				path: "field-attendance",
				name: "field-attendance",
				component: () => import("@/views/FieldAttendanceListView.vue"),
			},
			{
				path: "field-attendance/new",
				name: "field-attendance-new",
				component: () => import("@/views/NewFieldAttendanceView.vue"),
			},
			{
				path: "field-attendance/:id",
				name: "field-attendance-detail",
				component: () => import("@/views/FieldAttendanceDetailView.vue"),
				props: true,
			},
			{
				path: "labour-attendance",
				name: "labour-attendance",
				component: () => import("@/views/LabourAttendanceListView.vue"),
			},
			{
				path: "overtime-attendance",
				name: "overtime-attendance",
				component: () => import("@/views/OvertimeAttendanceListView.vue"),
			},
			{
				path: "scope-change",
				name: "scope-change",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Scope Change",
					icon: "🔁",
					desc: "Scope change orders live under Site Execution.",
					links: [
						{
							label: "Site Execution",
							to: "/site-execution",
							icon: "🏗️",
							desc: "Go to the workspace where SCOs now live",
						},
						{
							label: "Scope Change Orders",
							to: "/sco",
							icon: "🔁",
							desc: "Direct link to the SCO register",
						},
					],
				},
			},
			{
				path: "project-finance",
				name: "project-finance",
				component: () => import("@/views/workspaces/ProjectFinanceWorkspace.vue"),
			},
			{
				path: "project-finance/petty-cash",
				name: "petty-cash",
				component: () => import("@/views/finance/FinancePettyCashPanel.vue"),
			},
			{
				path: "project-finance/invoices/new",
				name: "finance-invoice-new",
				component: () => import("@/views/finance/FinanceInvoiceFormView.vue"),
			},
			{
				path: "project-finance/invoices/:id/edit",
				name: "finance-invoice-edit",
				component: () => import("@/views/finance/FinanceInvoiceFormView.vue"),
				props: true,
			},
			{
				path: "project-finance/invoices/:id",
				name: "finance-invoice",
				component: () => import("@/views/finance/FinanceInvoiceDetailView.vue"),
				props: true,
			},
			{
				path: "project-finance/invoices/:id/print",
				name: "finance-invoice-print",
				component: () => import("@/views/finance/FinanceInvoicePrintView.vue"),
				props: true,
			},
			{
				path: "project-finance/supplier-bills/new",
				name: "finance-supplier-bill-new",
				component: () => import("@/views/finance/FinanceSupplierBillFormView.vue"),
			},
			{
				path: "project-finance/supplier-bills/:id/edit",
				name: "finance-supplier-bill-edit",
				component: () => import("@/views/finance/FinanceSupplierBillFormView.vue"),
				props: true,
			},
			{
				path: "project-finance/supplier-bills/:id",
				name: "finance-supplier-bill",
				component: () => import("@/views/finance/FinanceSupplierBillDetailView.vue"),
				props: true,
			},
			{
				path: "procurement/report/:slug",
				name: "procurement-report",
				component: () => import("@/views/procurement/reports/ProcurementReportView.vue"),
				props: true,
			},
			{
				path: "project-finance/report/:slug",
				name: "finance-report",
				component: () => import("@/views/finance/FinanceReportPageView.vue"),
				props: true,
			},
			{
				path: "project-finance/:section",
				name: "finance-section",
				component: () => import("@/views/finance/FinancePageView.vue"),
				props: true,
			},

			{
				path: "accounting",
				name: "accounting",
				component: () => import("@/views/workspaces/AccountingWorkspace.vue"),
			},
			{
				path: "buying",
				name: "buying",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Buying",
					icon: "📥",
					desc: "Suppliers, purchase orders and request-for-quotation flows.",
				},
			},
			{
				path: "stock",
				name: "stock",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Stock",
					icon: "📦",
					desc: "Items, stock entries, warehouses and inventory.",
				},
			},
			{
				path: "assets",
				name: "assets",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Assets",
					icon: "🏭",
					desc: "Plant, machinery and asset register.",
				},
			},
			{
				path: "hr",
				name: "hr",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "HR",
					icon: "👤",
					desc: "Office staff records, leaves and salary.",
				},
			},

			{
				path: "subcontractor",
				name: "subcontractor",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Subcontractor",
					icon: "🤝",
					desc: "Vendors, RA Bills, retention, payments.",
				},
			},
			{
				path: "labour",
				name: "labour",
				component: () => import("@/views/PlaceholderView.vue"),
				props: { title: "Labour", icon: "👷", desc: "Attendance and overtime." },
			},
			{
				path: "financials",
				name: "financials",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Financials",
					icon: "💵",
					desc: "Petty cash, cost summary, variance reports.",
				},
			},
			{
				path: "reports",
				name: "reports",
				component: () => import("@/views/PlaceholderView.vue"),
				props: { title: "Reports", icon: "📑", desc: "Project intelligence reports." },
			},

			{
				path: "settings",
				name: "settings",
				component: () => import("@/views/settings/SettingsHubView.vue"),
			},
			{
				path: "settings/companies",
				name: "settings-companies",
				component: () => import("@/views/settings/CompaniesView.vue"),
			},
			{
				path: "settings/companies/new",
				name: "settings-company-new",
				component: () => import("@/views/settings/NewCompanyView.vue"),
			},
			{
				path: "settings/companies/:id",
				name: "settings-company-detail",
				component: () => import("@/views/settings/CompanyDetailView.vue"),
				props: true,
			},
			{
				path: "settings/users",
				name: "settings-users",
				component: () => import("@/views/settings/UsersView.vue"),
			},
			{
				path: "settings/users/new",
				name: "settings-user-new",
				component: () => import("@/views/settings/NewUserView.vue"),
			},
			{
				path: "settings/data",
				name: "settings-data",
				component: () => import("@/views/settings/DataToolsView.vue"),
			},
			{
				path: "settings/core",
				name: "settings-core",
				component: () => import("@/views/settings/CoreSettingsView.vue"),
			},
			{
				path: "settings/finance-accounts",
				name: "settings-finance-accounts",
				component: () => import("@/views/settings/FinanceAccountsView.vue"),
			},
			{
				path: "settings/workspaces",
				name: "settings-workspaces",
				component: () => import("@/views/settings/WorkspaceSettingsView.vue"),
			},
			// Legacy redirect — Site Execution Settings became the tabbed Workspace Setting.
			{
				path: "settings/site-execution",
				redirect: "/settings/workspaces",
			},
			{
				path: "settings/workspace-structure",
				name: "settings-workspace-structure",
				component: () => import("@/views/settings/WorkspaceStructureView.vue"),
			},
			{
				path: "settings/project-categories",
				name: "settings-project-categories",
				component: () => import("@/views/settings/ProjectCategoriesView.vue"),
			},
			{
				path: "settings/project-categories/new",
				name: "settings-project-category-new",
				component: () => import("@/views/settings/NewProjectCategoryView.vue"),
			},
			{
				path: "settings/project-categories/:id",
				name: "settings-project-category-detail",
				component: () => import("@/views/settings/ProjectCategoryDetailView.vue"),
				props: true,
			},
			{
				path: "settings/project-categories/:id/template",
				name: "settings-project-category-template",
				component: () => import("@/views/settings/ProjectTemplateEditorView.vue"),
				props: true,
			},
			{
				path: "settings/personas",
				name: "settings-personas",
				component: () => import("@/views/settings/PersonasView.vue"),
			},
			{
				path: "settings/personas/new",
				name: "settings-persona-new",
				component: () => import("@/views/settings/NewPersonaView.vue"),
			},
			{
				path: "settings/personas/:id",
				name: "settings-persona-detail",
				component: () => import("@/views/settings/PersonaDetailView.vue"),
				props: true,
			},
		],
	},
	{
		path: "/forbidden",
		name: "forbidden",
		component: () => import("@/views/AccessDeniedView.vue"),
		props: (route) => ({
			reason: route.query.reason || "missing_role",
			target: route.query.target || "/home",
		}),
	},
	{ path: "/:pathMatch(.*)*", redirect: "/home" },
];

const router = createRouter({
	history: createWebHistory(APP_ROUTE),
	routes,
	scrollBehavior() {
		return { top: 0 };
	},
});

router.beforeEach(async (to) => {
	const unprotected = new Set(["forbidden"]);
	if (unprotected.has(to.name)) return true;

	const sessionStore = useSessionStore();
	const access = await sessionStore.ensureAccess({ force: false });

	if (!sessionStore.authenticated) {
		window.location.assign(getLoginUrl(to.fullPath));
		return false;
	}

	if (!access?.allowed) {
		return {
			name: "forbidden",
			query: {
				reason: access?.reason || "missing_role",
				target: to.fullPath,
			},
		};
	}

	return true;
});

// Set a distinct browser title per route. A view may further refine it (e.g. to a
// record name) via usePageTitle once its data loads.
router.afterEach((to) => {
	const label = PAGE_TITLES[to.name];
	document.title = label ? `${label} · ${APP_TITLE}` : APP_TITLE;
});

export default router;
