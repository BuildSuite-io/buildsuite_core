<script setup>
// Project Finance workspace landing — standard workspace pattern (like Site
// Execution / Subcontract): a prominent Overview CTA + grouped WorkspaceShortcut
// tiles that open each function in its own page. Role-gated via the session roles
// (site roles see only Petty Cash + Expenses), mirroring the prototype's
// store.visibleFinanceTabs. Every section is client-side dummy data except Petty
// Cash, which is live.
import { computed, ref, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { storeToRefs } from "pinia";
import { useFinanceMock } from "@/data/financeMock";
import { useSessionStore } from "@/stores/session";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { getWorkspaceReports, getWorkspaceDoctypes } from "@/data/workspaceSettingApi";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { fmtINR } from "@/utils/format";

const fin = useFinanceMock();
const session = useSessionStore();
const { access } = storeToRefs(session);

const today = new Date().toLocaleDateString("en-US", {
	weekday: "long",
	month: "short",
	day: "numeric",
});
const cashBank = computed(() => fin.totalCashBank);

// Role gating — parity with the prototype's visibleFinanceTabs.
const FINANCE_SITE_ROLES = ["BuildSuite Site Engineer", "BuildSuite Foreman"];
const FINANCE_FULL_ROLES = [
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite Accountant",
	"BuildSuite QS",
	"BuildSuite Administrator",
	"System Manager",
	"Administrator",
];
const roles = computed(() => access.value?.roles || []);
const hasAny = (list) => roles.value.some((r) => list.includes(r));
const visibleSections = computed(() => {
	if (hasAny(FINANCE_FULL_ROLES))
		return [
			"overview",
			"petty-cash",
			"expenses",
			"customers",
			"suppliers",
			"invoices",
			"bills",
			"payments",
			"reports",
		];
	if (hasAny(FINANCE_SITE_ROLES)) return ["petty-cash", "expenses"];
	return [];
});
const canSee = (section) => visibleSections.value.includes(section);
const noAccess = computed(() => !visibleSections.value.length);

// Per the prototype's Site Execution rule (S50), DocType shortcut tiles render WITHOUT a
// description — only the Reports group below carries subtext.
const TRANSACTIONS = [
	{ section: "petty-cash", icon: "hand-coins", label: "Petty Cash" },
	{ section: "expenses", icon: "receipt", label: "Expenses" },
	{ section: "invoices", icon: "file-text", label: "Invoices" },
	{ section: "bills", icon: "banknote", label: "Bills" },
	{ section: "payments", icon: "refresh-ccw", label: "Payments" },
];
const MASTERS = [
	{ section: "customers", icon: "users-round", label: "Customers" },
	{ section: "suppliers", icon: "building-2", label: "Suppliers" },
];
// Report tiles are configured per workspace in Workspace Setting (same as Site Execution /
// Procurement) — the standard ERPNext finance reports through the in-app renderer plus the
// BuildSuite-specific Petty Cash / Expense Summary. Each tile is role-gated server-side, so
// a persona without the Accounts roles simply gets none.
const reports = ref([]);
const records = ref([]);
onMounted(async () => {
	try {
		reports.value = await getWorkspaceReports("project-finance");
	} catch {
		reports.value = [];
	}
	try {
		records.value = await getWorkspaceDoctypes("project-finance");
	} catch {
		records.value = [];
	}
});

const txTiles = computed(() => TRANSACTIONS.filter((t) => canSee(t.section)));
const masterTiles = computed(() => MASTERS.filter((t) => canSee(t.section)));
const showReports = computed(() => canSee("reports") && reports.value.length > 0);
const showRecords = computed(() => records.value.length > 0);
const showOverview = computed(() => canSee("overview"));
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<!-- Title strip -->
			<div class="mb-5">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">Project Finance</h1>
			</div>

			<div
				v-if="noAccess"
				class="bg-warning-50 border border-warning-200 rounded-lg px-4 py-6 text-sm text-warning-700"
			>
				You don't have access to Project Finance.
			</div>

			<template v-else>
				<!-- Overview CTA -->
				<RouterLink
					v-if="showOverview"
					to="/project-finance/overview"
					class="mb-6 block bg-brand-50 border border-brand-200 hover:border-brand-400 hover:shadow-sm p-4 transition-all group rounded-lg"
				>
					<div class="flex items-center gap-4">
						<div
							class="w-11 h-11 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center flex-shrink-0"
						>
							<svg
								class="w-[22px] h-[22px]"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath('wallet')"
							/>
						</div>
						<div class="flex-1 min-w-0">
							<div
								class="text-base font-semibold text-ink-900 group-hover:text-brand-700 transition-colors"
							>
								Financial Overview
							</div>
							<div class="text-xs text-ink-600 mt-0.5">
								Cash &amp; bank balances, quick actions and alerts.
							</div>
						</div>
						<div class="text-right mr-2">
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
							>
								Cash &amp; bank
							</div>
							<div
								class="text-lg font-semibold text-ink-900 tabular-nums leading-none"
							>
								{{ fmtINR(cashBank) }}
							</div>
						</div>
						<div
							class="text-brand-400 group-hover:text-brand-600 transition-colors text-xl"
						>
							→
						</div>
					</div>
				</RouterLink>

				<!-- Transactions -->
				<div v-if="txTiles.length" class="mb-8">
					<h2
						class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2"
					>
						Transactions
					</h2>
					<div class="border-t border-ink-200 mb-3"></div>
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
						<WorkspaceShortcut
							v-for="t in txTiles"
							:key="t.section"
							:icon="t.icon"
							:label="t.label"
							:to="`/project-finance/${t.section}`"
						/>
					</div>
				</div>

				<!-- Masters -->
				<div v-if="masterTiles.length" class="mb-8">
					<h2
						class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2"
					>
						Masters
					</h2>
					<div class="border-t border-ink-200 mb-3"></div>
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
						<WorkspaceShortcut
							v-for="t in masterTiles"
							:key="t.section"
							:icon="t.icon"
							:label="t.label"
							:to="`/project-finance/${t.section}`"
						/>
					</div>
				</div>

				<!-- Records (admin-curated DocTypes) -->
				<div v-if="showRecords" class="mb-8">
					<h2
						class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2"
					>
						Records
					</h2>
					<div class="border-t border-ink-200 mb-3"></div>
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
						<WorkspaceShortcut
							v-for="(d, i) in records"
							:key="i"
							:icon="d.icon"
							:label="d.label"
							:description="d.description"
							:to="d.route"
						>
							<template #badge>
								<span
									class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 font-medium uppercase tracking-wider"
									style="border-radius: 2px"
									>Records</span
								>
							</template>
						</WorkspaceShortcut>
					</div>
				</div>

				<!-- Reports -->
				<div v-if="showReports" class="mb-4">
					<h2
						class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2"
					>
						Reports
					</h2>
					<div class="border-t border-ink-200 mb-3"></div>
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
						<WorkspaceShortcut
							v-for="(r, i) in reports"
							:key="i"
							:icon="r.icon"
							:label="r.label"
							:description="r.description"
							:to="r.external ? null : r.route"
							:href="r.external ? r.route : null"
						>
							<template #badge>
								<span
									class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 font-medium uppercase tracking-wider"
									style="border-radius: 2px"
									>Report</span
								>
							</template>
						</WorkspaceShortcut>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>
