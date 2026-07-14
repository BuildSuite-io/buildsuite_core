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
	estimation: "Estimation",
	procurement: "Procurement",
	"procurement-dashboard": "Procurement Dashboard",
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
	workforce: "Workforce",
	"scope-change": "Scope Change",
	"project-finance": "Project Finance",
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
	"settings-site-execution": "Site Execution Settings",
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
			{ path: "sco/new", name: "sco-new", component: () => import("@/views/NewScoView.vue") },
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
				path: "workforce",
				name: "workforce",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Workforce",
					icon: "👷",
					desc: "Crew assignment, overtime and wages-to-contractor.",
				},
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
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Project Finance",
					icon: "💵",
					desc: "Petty cash, cost summary, project P&L and variance reports.",
				},
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
				path: "settings/site-execution",
				name: "settings-site-execution",
				component: () => import("@/views/settings/SiteExecutionSettingsView.vue"),
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
