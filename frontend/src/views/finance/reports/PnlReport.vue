<script setup>
// Profit & Loss — our own account-tree variant (buildsuite_core.api.finance_report.
// profit_and_loss), NOT the stock ERPNext financial statement, so the labels + layout are
// ours: an Income / Direct Expenses / Indirect Expenses tree with a "Profit" line (the period
// is whatever the date filter says, rarely a fiscal year — so "Profit", not "Profit for the
// year"). Figures come live from the posted GL, scoped by project + period. Clicking a leaf
// lists its contributing vouchers — the in-app stand-in for drilling into the ledger.
import { ref, computed, watch, onMounted } from "vue";
import { useRoute } from "vue-router";

import DeskPage from "@/components/desk/DeskPage.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { getProfitAndLoss } from "@/data/financeReportApi";
import { fmtINR, fmtDate } from "@/utils/format";

const route = useRoute();
const breadcrumbs = [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Profit & Loss" },
];

// ?project= preselects, so a project's Reports list deep-links into its P&L.
const projectId = ref(route.query.project || "");
const from = ref("");
const to = ref("");
const accountQuery = ref("");
const hideEmpty = ref(false);

const data = ref({ income: [], directExpenses: [], indirectExpenses: [], totals: {} });
const loading = ref(true);
const error = ref("");

async function load() {
	loading.value = true;
	error.value = "";
	try {
		data.value = await getProfitAndLoss({
			project: projectId.value || undefined,
			from_date: from.value || undefined,
			to_date: to.value || undefined,
		});
	} catch (e) {
		error.value = e.message || "Failed to load.";
	} finally {
		loading.value = false;
	}
}
onMounted(load);
watch([projectId, from, to], load);

const income = computed(() => data.value.income || []);
const directExpenses = computed(() => data.value.directExpenses || []);
const indirectExpenses = computed(() => data.value.indirectExpenses || []);
const incomeTotal = computed(() => Number(data.value.totals?.income) || 0);
const directTotal = computed(() => Number(data.value.totals?.direct) || 0);
const indirectTotal = computed(() => Number(data.value.totals?.indirect) || 0);
const expenseTotal = computed(() => Number(data.value.totals?.expense) || 0);
const profit = computed(() => Number(data.value.totals?.profit) || 0);
// Margin against income — the one ratio a P&L reader asks for straight away.
const marginPct = computed(() => (incomeTotal.value ? (profit.value / incomeTotal.value) * 100 : 0));

const anyFilter = computed(
	() => !!from.value || !!to.value || !!projectId.value || hideEmpty.value || !!accountQuery.value
);
function clearFilters() {
	from.value = "";
	to.value = "";
	projectId.value = "";
	hideEmpty.value = false;
	accountQuery.value = "";
}

const collapsed = ref({});
function toggleGroup(key) {
	collapsed.value = { ...collapsed.value, [key]: !collapsed.value[key] };
}
const openDocs = ref(null);
function toggleDocs(key) {
	openDocs.value = openDocs.value === key ? null : key;
}

// Leaves only — a group or total row is structure, never filtered away, or the statement
// stops reading as a statement.
function keepLeaf(r) {
	if (r.kind !== "leaf") return true;
	if (hideEmpty.value && !r.amount) return false;
	if (
		accountQuery.value &&
		!String(r.label || "")
			.toLowerCase()
			.includes(accountQuery.value.trim().toLowerCase())
	)
		return false;
	return true;
}

const rows = computed(() => {
	const out = [];
	const c = collapsed.value;

	out.push({ kind: "group", key: "income", label: "Income", level: 0, amount: incomeTotal.value });
	if (!c.income) {
		out.push({ kind: "group", key: "direct-income", label: "Direct Income", level: 1, amount: incomeTotal.value });
		if (!c["direct-income"]) {
			for (const a of income.value)
				out.push({ kind: "leaf", key: `inc-${a.name}`, label: a.name, level: 2, amount: a.amount, docs: a.docs });
		}
	}
	out.push({ kind: "total", label: "Total Income (Credit)", amount: incomeTotal.value });
	out.push({ kind: "spacer" });

	out.push({ kind: "group", key: "expenses", label: "Expenses", level: 0, amount: expenseTotal.value });
	if (!c.expenses) {
		if (directExpenses.value.length) {
			out.push({ kind: "group", key: "direct-exp", label: "Direct Expenses", level: 1, amount: directTotal.value });
			if (!c["direct-exp"])
				for (const a of directExpenses.value)
					out.push({ kind: "leaf", key: `d-${a.name}`, label: a.name, level: 2, amount: a.amount, docs: a.docs });
		}
		if (indirectExpenses.value.length) {
			out.push({ kind: "group", key: "indirect-exp", label: "Indirect Expenses", level: 1, amount: indirectTotal.value });
			if (!c["indirect-exp"])
				for (const a of indirectExpenses.value)
					out.push({ kind: "leaf", key: `i-${a.name}`, label: a.name, level: 2, amount: a.amount, docs: a.docs });
		}
	}
	out.push({ kind: "total", label: "Total Expense (Debit)", amount: expenseTotal.value });
	out.push({ kind: "spacer" });
	// "Profit", not "Profit for the year": the period is whatever the date filter says.
	out.push({ kind: "profit", label: "Profit", amount: profit.value });
	return out.filter(keepLeaf);
});
const leafCount = computed(() => rows.value.filter((r) => r.kind === "leaf").length);

const periodLabel = computed(() => {
	if (from.value && to.value) return `${fmtDate(from.value)} → ${fmtDate(to.value)}`;
	if (from.value) return `From ${fmtDate(from.value)}`;
	if (to.value) return `To ${fmtDate(to.value)}`;
	return "All dates";
});
function indentStyle(level) {
	return `padding-left:${12 + level * 18}px`;
}
</script>

<template>
	<DeskPage title="Profit &amp; Loss" :breadcrumbs="breadcrumbs" printable>
		<div v-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<div v-else>
			<ReportFilters :active="anyFilter" :shown="leafCount" noun="accounts" @clear="clearFilters">
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Project</span>
					<span class="w-52 inline-block">
						<DeskLinkPicker
							v-model="projectId"
							doctype="Project"
							label-field="project_name"
							value-field="name"
							:search-fields="['project_name', 'name']"
							placeholder="All projects"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Period</span>
					<DeskInput v-model="from" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">to</span>
					<DeskInput v-model="to" type="date" class="!w-36" />
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Find</span>
					<DeskInput v-model="accountQuery" placeholder="Account name…" class="!w-44" />
				</label>
				<label class="flex items-center gap-1.5 cursor-pointer">
					<input type="checkbox" v-model="hideEmpty" class="accent-brand-600" />
					<span class="text-[11px] text-ink-600">Hide empty accounts</span>
				</label>
			</ReportFilters>

			<!-- Summary tiles — the four figures asked for first; they mirror the tree's own
			     breakdown rather than inventing a different one. -->
			<div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
				<div class="bg-white border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Total income</div>
					<div class="text-lg font-semibold text-ink-900 tabular-nums mt-1 whitespace-nowrap">
						{{ fmtINR(incomeTotal) }}
					</div>
					<div class="text-[10px] text-ink-400 mt-0.5">posted invoices</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Direct expenses</div>
					<div class="text-lg font-semibold text-ink-900 tabular-nums mt-1 whitespace-nowrap">
						{{ fmtINR(directTotal) }}
					</div>
					<div class="text-[10px] text-ink-400 mt-0.5 tabular-nums">
						{{ incomeTotal ? ((directTotal / incomeTotal) * 100).toFixed(1) + "% of income" : "cost of sales" }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Indirect expenses</div>
					<div class="text-lg font-semibold text-ink-900 tabular-nums mt-1 whitespace-nowrap">
						{{ fmtINR(indirectTotal) }}
					</div>
					<div class="text-[10px] text-ink-400 mt-0.5">overheads</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Profit</div>
					<div
						class="text-lg font-semibold tabular-nums mt-1 whitespace-nowrap"
						:class="profit < 0 ? 'text-danger-600' : 'text-success-700'"
					>
						{{ fmtINR(profit) }}
					</div>
					<div
						class="text-[10px] mt-0.5 tabular-nums"
						:class="profit < 0 ? 'text-danger-600' : 'text-success-700'"
					>
						{{ incomeTotal ? marginPct.toFixed(1) + "% margin" : "no income in period" }}
					</div>
				</div>
			</div>

			<!-- Statement -->
			<div class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<table class="w-full text-xs">
					<thead
						class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200"
					>
						<tr>
							<th class="w-10 text-right px-2 py-2 font-medium"></th>
							<th class="text-left px-3 py-2 font-medium">Account</th>
							<th class="text-right px-4 py-2 font-medium whitespace-nowrap">{{ periodLabel }}</th>
						</tr>
					</thead>
					<tbody>
						<template v-for="(r, i) in rows" :key="r.key || `${r.kind}-${i}`">
							<tr v-if="r.kind === 'spacer'" class="border-b border-ink-100">
								<td class="px-2 py-2 text-right text-ink-300 tabular-nums">{{ i + 1 }}</td>
								<td colspan="2"></td>
							</tr>
							<tr
								v-else
								class="border-b border-ink-100"
								:class="[
									r.kind === 'total' || r.kind === 'profit' ? 'bg-ink-50/60 font-semibold' : 'hover:bg-brand-50/30',
									r.kind === 'group' || r.kind === 'leaf' ? 'cursor-pointer' : '',
								]"
								@click="
									r.kind === 'group' ? toggleGroup(r.key) : r.kind === 'leaf' ? toggleDocs(r.key) : null
								"
							>
								<td class="px-2 py-2 text-right text-ink-300 tabular-nums align-top">{{ i + 1 }}</td>
								<td class="py-2 pr-3" :style="r.level != null ? indentStyle(r.level) : 'padding-left:12px'">
									<span class="flex items-center gap-1.5">
										<svg
											v-if="r.kind === 'group'"
											class="w-3 h-3 text-ink-400 flex-shrink-0 transition-transform"
											:class="collapsed[r.key] ? '-rotate-90' : ''"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2.5"
											stroke-linecap="round"
											stroke-linejoin="round"
										>
											<polyline points="6 9 12 15 18 9" />
										</svg>
										<span
											:class="[
												r.kind === 'group' ? 'font-semibold text-ink-900' : '',
												r.kind === 'leaf' ? 'text-ink-700' : '',
												r.kind === 'total' || r.kind === 'profit' ? 'text-ink-900' : '',
											]"
											>{{ r.label }}</span
										>
									</span>
								</td>
								<td
									class="px-4 py-2 text-right tabular-nums whitespace-nowrap"
									:class="r.kind === 'profit' && r.amount < 0 ? 'text-danger-600' : 'text-ink-900'"
								>
									{{ fmtINR(r.amount) }}
								</td>
							</tr>

							<!-- Contributing vouchers — the in-app stand-in for drilling into the GL. -->
							<tr
								v-if="r.kind === 'leaf' && openDocs === r.key"
								class="border-b border-ink-100 bg-ink-50/40"
							>
								<td></td>
								<td colspan="2" class="px-4 py-2">
									<div v-if="r.docs && r.docs.length" class="space-y-1">
										<div
											v-for="(d, di) in r.docs"
											:key="di"
											class="flex items-center justify-between gap-4 text-[11px]"
										>
											<span class="min-w-0">
												<span class="text-ink-800">{{ d.label }}</span>
												<span class="text-ink-400 ml-1.5">{{ d.sub }}</span>
											</span>
											<span class="tabular-nums text-ink-700 flex-shrink-0">{{ fmtINR(d.amount) }}</span>
										</div>
									</div>
									<div v-else class="text-[11px] text-ink-400 italic">No contributing vouchers.</div>
								</td>
							</tr>
						</template>
						<tr v-if="loading">
							<td colspan="3" class="px-4 py-8 text-center text-sm text-ink-400 italic">Loading…</td>
						</tr>
					</tbody>
				</table>
			</div>

			<p class="text-[11px] text-ink-400 mt-2 print:hidden">
				Income and expenses are posted GL entries, grouped by ledger account and scoped to the
				selected project and period. Direct vs indirect follows the chart of accounts' cost-of-sales
				boundary. Click an account to list its vouchers.
			</p>
		</div>
	</DeskPage>
</template>
