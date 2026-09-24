<script setup>
// Role-aware Home. One live aggregate read (api.home.get_home_dashboard) returns the
// logged-in user's snapshot tiles, primary CTA and alert cards — the same per-role content
// as the prototype's HomeWorkspaceView. This view is a thin renderer of that payload.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useSessionStore } from "@/stores/session";
import { useUserNames } from "@/composables/useUserNames";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { fmtCompactINR } from "@/utils/format";
import { getHomeDashboard } from "@/data/homeDashboardApi";

const store = useDataStore();
const session = useSessionStore();
const { userName: resolveUserName } = useUserNames();
const activeCompany = useActiveCompany();

const dash = ref(null);
async function load() {
	try {
		dash.value = await getHomeDashboard();
	} catch {
		dash.value = null;
	}
}
onMounted(load);
// The dashboard is scoped to the working company (get_home_dashboard → default_company); reload it
// when the switcher changes so the home snapshot follows the company.
watch(activeCompany, load);

const snapshot = computed(() => dash.value?.snapshot || []);
const alerts = computed(() => dash.value?.alerts || []);
const cta = computed(() => dash.value?.cta || null);

const now = new Date();
const greeting = computed(() => {
	const hour = now.getHours();
	if (hour < 12) return "Good morning";
	if (hour < 18) return "Good afternoon";
	return "Good evening";
});
const userName = computed(() => {
	const id = session.user && session.user !== "Guest" ? session.user : null;
	return (id && resolveUserName(id)) || store.user?.name || "Admin User";
});
const roleLabel = computed(() =>
	store.isAdmin ? "System Manager (Admin)" : store.currentRole?.name || "User"
);
const greetingSub = computed(
	() => dash.value?.greeting_sub || "Here is a snapshot of your work today."
);
const dateLabel = computed(() =>
	new Intl.DateTimeFormat("en-GB", {
		weekday: "long",
		day: "2-digit",
		month: "short",
		year: "numeric",
	}).format(now)
);
const initials = computed(() => {
	const name = userName.value || "A D";
	const parts = name.split(" ").filter(Boolean);
	if (!parts.length) return "AD";
	if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
	return `${parts[0][0] || ""}${parts[1][0] || ""}`.toUpperCase();
});

// tone → icon chip classes (shared by snapshot tiles + alert cards).
const TONE = {
	brand: "bg-brand-50 text-brand-700",
	info: "bg-info-50 text-info-700",
	success: "bg-success-50 text-success-700",
	warning: "bg-warning-50 text-warning-700",
	danger: "bg-danger-50 text-danger-700",
	muted: "bg-ink-50 text-ink-400",
};
function toneClass(t) {
	return TONE[t] || TONE.brand;
}
function tileValue(m) {
	return m.format === "currency" ? fmtCompactINR(m.value) : m.value;
}

// Role-gated quick actions — each persona sees only the tiles for its slug, matching
// the prototype's per-role Home. `store.role` is the persona slug; ALL_ACTIONS lists
// every tile with the roles allowed to see it, and quickActions filters to the caller.
const ALL_ACTIONS = [
	{ key:'projects',      label:'Projects',            to:'/projects',                      icon:'clipboard-list', roles:['director','pm','site-engineer','foreman','estimator','qs','accountant'] },
	{ key:'tasks',         label:'Tasks',               to:'/tasks',                         icon:'check-circle',   roles:['director','pm','site-engineer','foreman'] },
	{ key:'progress-new',  label:'File Progress Entry', to:'/progress-entries/new',          icon:'file-text',      roles:['pm','site-engineer','foreman'] },
	{ key:'schedule',      label:'Schedule',            to:'/schedule',                      icon:'calendar',       roles:['director','pm','site-engineer'] },
	{ key:'stages',        label:'Stage Planning',      to:'/stage-plannings',               icon:'layout-grid',    roles:['pm','site-engineer'] },
	{ key:'boq',           label:'BOQ',                 to:'/boq',                           icon:'estimation',     roles:['director','pm','estimator','qs'] },
	{ key:'rate-master',   label:'Rate Master',         to:'/rate-master',                   icon:'chart-bar',      roles:['estimator','qs'] },
	{ key:'assemblies',    label:'Assemblies',          to:'/assembly',                      icon:'wrench',         roles:['estimator'] },
	{ key:'sub-wos',       label:'Work Orders',         to:'/subcontractor-work-orders',     icon:'subcontract',    roles:['pm','qs','director'] },
	{ key:'sub-bills',     label:'Subcontractor Bills', to:'/subcontractor-bills',           icon:'receipt',        roles:['qs','accountant'] },
	{ key:'mrs',           label:'Material Requests',   to:'/procurement/material-requests', icon:'clipboard-list', roles:['pm','procurement','store-keeper','site-engineer','foreman'] },
	{ key:'pos',           label:'Purchase Orders',     to:'/procurement/purchase-orders',   icon:'file-text',      roles:['procurement','store-keeper'] },
	{ key:'grns',          label:'Purchase Receipts',   to:'/procurement/receipts',          icon:'stock',          roles:['procurement','store-keeper'] },
	{ key:'grn-new',       label:'Confirm Delivery',    to:'/procurement/receipts/new',      icon:'stock',          roles:['site-engineer','foreman'] },
	{ key:'consumption',   label:'Record Consumption',  to:'/material-consumption/new',      icon:'package',        roles:['store-keeper','site-engineer','foreman'] },
	{ key:'items',         label:'Items',               to:'/items',                         icon:'tag',            roles:['procurement','store-keeper'] },
	{ key:'suppliers',     label:'Suppliers',           to:'/project-finance/suppliers',     icon:'building-2',     roles:['procurement'] },
	{ key:'fin-invoices',  label:'Invoices',            to:'/project-finance/invoices',      icon:'file-text',      roles:['accountant'] },
	{ key:'fin-bills',     label:'Bills',               to:'/project-finance/bills',         icon:'receipt',        roles:['accountant'] },
	{ key:'fin-payments',  label:'Payments',            to:'/project-finance/payments',      icon:'refresh-ccw',    roles:['accountant'] },
	{ key:'fin-petty',     label:'Petty Cash',          to:'/project-finance/petty-cash',    icon:'hand-coins',     roles:['accountant','director','site-engineer','foreman'] },
	{ key:'fin-expenses',  label:'Expenses',            to:'/project-finance/expenses',      icon:'receipt',        roles:['director','site-engineer','foreman'] },
	{ key:'fin-overview',  label:'Financial Overview',  to:'/project-finance/overview',      icon:'wallet',         roles:['director'] },
	{ key:'wf-attendance', label:'Field Attendance',    to:'/field-attendance',              icon:'users-2',        roles:['foreman','hr-manager','site-engineer'] },
	{ key:'wf-employees',  label:'Field Employees',     to:'/field-employees',               icon:'hard-hat',       roles:['hr-manager'] },
	{ key:'wf-crews',      label:'Crews',               to:'/crews',                         icon:'users-2',        roles:['foreman','hr-manager'] },
	{ key:'wf-labour',     label:'Labour Register',     to:'/labour-attendance',             icon:'clipboard-list', roles:['hr-manager'] },
	{ key:'admin-users',      label:'Users',              to:'/settings/users',           icon:'users-2',        roles:['admin','bsa'] },
	{ key:'admin-projects',   label:'Projects',           to:'/projects',                 icon:'clipboard-list', roles:['admin','bsa'] },
	{ key:'admin-dashboard',  label:'Project Dashboard',  to:'/project-dashboard',        icon:'chart-bar',      roles:['admin','bsa'] },
	{ key:'admin-boq',        label:'BOQ',                to:'/boq',                      icon:'estimation',     roles:['admin','bsa'] },
	{ key:'admin-finance',    label:'Financial Overview', to:'/project-finance/overview', icon:'wallet',         roles:['admin','bsa'] },
	{ key:'admin-attendance', label:'Field Attendance',   to:'/field-attendance',         icon:'users-2',        roles:['admin','bsa'] },
];
// Site roles re-sort their tiles by daily frequency.
const SITE_ROLES = ["site-engineer", "foreman"];
const SITE_ACTION_ORDER = ["wf-attendance","progress-new","tasks","consumption","grn-new","mrs","fin-petty","fin-expenses","stages","schedule","projects"];
const quickActions = computed(() => {
	const list = ALL_ACTIONS.filter((a) => a.roles.includes(store.role));
	if (!SITE_ROLES.includes(store.role)) return list;
	const rank = (a) => { const i = SITE_ACTION_ORDER.indexOf(a.key); return i === -1 ? SITE_ACTION_ORDER.length : i; };
	return list.slice().sort((a, b) => rank(a) - rank(b));
});
</script>

<template>
	<div class="px-6 py-8 max-w-6xl mx-auto">
		<!-- Greeting -->
		<div class="flex items-start gap-4 mb-6">
			<div class="inline-flex items-center gap-2">
				<div
					class="w-12 h-12 text-base bg-brand-600 rounded-full flex items-center justify-center text-white font-medium flex-shrink-0"
				>
					{{ initials }}
				</div>
			</div>
			<div class="flex-1 min-w-0">
				<div class="text-sm text-ink-500">{{ greeting }},</div>
				<h1 class="text-2xl font-semibold text-ink-900 mt-0.5">{{ userName }}</h1>
				<p class="text-sm text-ink-500 mt-1.5">{{ greetingSub }}</p>
				<div class="text-[11px] text-ink-400 mt-1 flex flex-wrap items-center gap-x-2">
					<span>{{ roleLabel }}</span>
					<span class="text-ink-300">·</span>
					<span>{{ dateLabel }}</span>
				</div>
			</div>
		</div>

		<!-- Snapshot + CTA -->
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
			<section
				class="lg:col-span-2 bg-white border border-ink-200 rounded-lg overflow-hidden"
			>
				<header
					class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">Today's snapshot</h2>
					<span
						class="text-[10px] uppercase tracking-wider font-medium text-success-700 bg-success-50 px-2 py-0.5 rounded-full inline-flex items-center gap-1"
					>
						<span class="w-1.5 h-1.5 rounded-full bg-success-500"></span>
						Live
					</span>
				</header>
				<div class="p-5">
					<div class="grid grid-cols-2 sm:grid-cols-4 gap-5">
						<component
							:is="m.to ? 'RouterLink' : 'div'"
							v-for="m in snapshot"
							:key="m.label"
							:to="m.to || undefined"
							class="block -m-2 p-2 rounded-lg"
							:class="m.to ? 'cursor-pointer hover:bg-ink-50 transition-colors' : ''"
						>
							<div
								class="w-11 h-11 rounded-lg flex items-center justify-center mb-3"
								:class="toneClass(m.tone)"
							>
								<svg
									width="22"
									height="22"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
									v-html="getWorkspaceIconPath(m.slug)"
								/>
							</div>
							<div
								class="font-semibold text-ink-900 tabular-nums leading-none"
								:class="m.format === 'currency' ? 'text-2xl' : 'text-3xl'"
							>
								{{ tileValue(m) }}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-2"
							>
								{{ m.label }}
							</div>
						</component>
					</div>
				</div>
			</section>

			<RouterLink
				v-if="cta"
				:to="cta.to"
				class="bg-brand-50 hover:bg-brand-100 rounded-lg p-5 flex flex-col justify-between transition-colors group"
			>
				<div class="flex items-start gap-3">
					<div
						class="w-9 h-9 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center flex-shrink-0"
					>
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath(cta.slug)"
						/>
					</div>
					<div class="min-w-0">
						<h2 class="text-base font-semibold text-ink-900 leading-tight">
							{{ cta.title }}
						</h2>
						<p class="text-xs text-ink-600 mt-1.5 leading-snug">{{ cta.sub }}</p>
					</div>
				</div>
				<div
					class="mt-4 inline-flex items-center gap-1.5 bg-brand-600 group-hover:bg-brand-700 text-white text-xs font-medium px-2.5 py-1.5 rounded-md self-start transition-colors"
				>
					{{ cta.cta }} <span aria-hidden="true">→</span>
				</div>
			</RouterLink>
		</div>

		<!-- Alert cards -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
			<RouterLink
				v-for="a in alerts"
				:key="a.key"
				:to="a.to"
				class="bg-white border border-ink-200 hover:border-brand-400 rounded-lg p-4 flex items-center gap-3 transition-colors group"
			>
				<div
					class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
					:class="toneClass(a.tone)"
				>
					<svg
						width="18"
						height="18"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.75"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
						v-html="getWorkspaceIconPath(a.slug)"
					/>
				</div>
				<div class="flex-1 min-w-0">
					<div class="text-sm font-semibold text-ink-900">{{ a.title }}</div>
					<div class="text-xs text-ink-500 mt-0.5 truncate">{{ a.sub }}</div>
				</div>
				<div
					class="text-xs text-brand-700 group-hover:text-brand-800 font-medium flex-shrink-0"
				>
					View →
				</div>
			</RouterLink>
		</div>

		<!-- Quick actions -->
		<div class="mb-6">
			<h2 class="text-sm font-semibold text-ink-900 mb-3">Quick actions</h2>
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				<RouterLink
					v-for="action in quickActions"
					:key="action.to"
					:to="action.to"
					class="bg-white border border-ink-200 hover:border-brand-400 hover:shadow-sm p-4 rounded-lg flex items-center gap-3 group transition-all"
				>
					<div
						class="w-10 h-10 rounded-lg bg-ink-50 group-hover:bg-brand-50 text-ink-600 group-hover:text-brand-700 flex items-center justify-center flex-shrink-0 transition-colors"
					>
						<svg
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath(action.icon)"
						/>
					</div>
					<div class="flex-1 min-w-0">
						<div
							class="text-sm font-medium text-ink-900 group-hover:text-brand-700 transition-colors"
						>
							{{ action.label }}
						</div>
					</div>
					<div class="text-ink-300 group-hover:text-brand-500 transition-colors">→</div>
				</RouterLink>
			</div>
		</div>
	</div>
</template>
