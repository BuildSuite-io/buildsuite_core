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
	assembly: "Assemblies",
	"assembly-new": "New Assembly",
	"assembly-detail": "Assembly",
	"site-execution": "Site Execution",
	"project-dashboard": "Project Dashboard",
	"report-stub": "Report",
	estimation: "Estimation",
	procurement: "Procurement",
	subcontract: "Subcontract",
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
	"settings-project-types": "Project Types",
	"settings-project-type-new": "New Project Type",
	"settings-project-type-detail": "Project Type",
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
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Procurement",
					icon: "🛒",
					desc: "Material requests, supplier follow-up and goods receipt.",
				},
			},
			{
				path: "subcontract",
				name: "subcontract",
				component: () => import("@/views/PlaceholderView.vue"),
				props: {
					title: "Subcontract",
					icon: "🤝",
					desc: "Vendors, work orders, measurement books, RA bills and retention.",
				},
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
				path: "settings/project-types",
				name: "settings-project-types",
				component: () => import("@/views/settings/ProjectTypesView.vue"),
			},
			{
				path: "settings/project-types/new",
				name: "settings-project-type-new",
				component: () => import("@/views/settings/NewProjectTypeView.vue"),
			},
			{
				path: "settings/project-types/:id",
				name: "settings-project-type-detail",
				component: () => import("@/views/settings/ProjectTypeDetailView.vue"),
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
