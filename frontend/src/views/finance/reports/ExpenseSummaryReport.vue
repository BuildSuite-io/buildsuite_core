<script setup>
// Expense Summary (PF). Group submitted expenses by project / expense account / cost code /
// paid-from / person, with a period filter, search + dimension filters, and drill-down to the
// entries (with a receipt thumbnail). Submitted expenses only — they're what hits the books.
import { computed, onMounted, reactive, ref } from "vue";

import DeskInput from "@/components/desk/DeskInput.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { listExpenses } from "@/data/expenseEntryApi";
import { fmtDate, fmtINR } from "@/utils/format";

const breadcrumbs = [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Expense Summary" },
];

const GROUPINGS = [
	{ key: "project", label: "Project" },
	{ key: "expense_account", label: "Expense account" },
	{ key: "cost_code", label: "Cost code" },
	{ key: "source", label: "Paid from" },
	{ key: "holder", label: "Person" },
];

const all = ref([]);
const loading = ref(true);
const error = ref("");

onMounted(async () => {
	try {
		const rows = await listExpenses();
		all.value = (rows || []).filter((e) => e.status === "Submitted");
	} catch (e) {
		error.value = e.message || "Failed to load expenses.";
	} finally {
		loading.value = false;
	}
});

const groupBy = ref("project");
const from = ref("");
const to = ref("");
const expanded = ref(null);

const BLANK = { q: "", project: "", account: "", source: "", holder: "" };
const f = reactive({ ...BLANK });
const anyFilter = computed(
	() => !!from.value || !!to.value || Object.keys(BLANK).some((k) => f[k] !== BLANK[k])
);
function clearFilters() {
	Object.assign(f, BLANK);
	from.value = "";
	to.value = "";
}
const hit = (hay, needle) =>
	!needle ||
	String(hay || "")
		.toLowerCase()
		.includes(needle.trim().toLowerCase());

function projectName(e) {
	return e.project ? e.project_name || e.project : "No project";
}
function holderName(e) {
	return e.employee_name || e.employee || "—";
}
function keyLabel(e) {
	if (groupBy.value === "project") return projectName(e);
	if (groupBy.value === "holder") return holderName(e);
	if (groupBy.value === "source") return e.source || "—";
	return e[groupBy.value] || "—";
}

// Pickers are built from the posted expenses themselves, so no option offers a value with
// nothing behind it.
const distinct = (pick, label) =>
	computed(() =>
		[...new Set(all.value.map(pick).filter(Boolean))]
			.map((v) => ({ value: v, label: label ? label(v) : v }))
			.sort((a, b) => a.label.localeCompare(b.label))
	);
const projectOptions = computed(() => {
	const m = new Map();
	for (const e of all.value) if (e.project) m.set(e.project, e.project_name || e.project);
	return [...m.entries()]
		.map(([value, label]) => ({ value, label }))
		.sort((a, b) => a.label.localeCompare(b.label));
});
const accountOptions = distinct((e) => e.expense_account);
const sourceOptions = distinct((e) => e.source);
const holderOptions = computed(() => {
	const m = new Map();
	for (const e of all.value) if (e.employee) m.set(e.employee, e.employee_name || e.employee);
	return [...m.entries()]
		.map(([value, label]) => ({ value, label }))
		.sort((a, b) => a.label.localeCompare(b.label));
});

const filtered = computed(() =>
	all.value.filter(
		(e) =>
			(!from.value || (e.date || "") >= from.value) &&
			(!to.value || (e.date || "") <= to.value) &&
			(!f.project || e.project === f.project) &&
			(!f.account || e.expense_account === f.account) &&
			(!f.source || e.source === f.source) &&
			(!f.holder || e.employee === f.holder) &&
			(hit(e.description, f.q) || hit(e.name, f.q) || hit(projectName(e), f.q))
	)
);

const groups = computed(() => {
	const m = new Map();
	for (const e of filtered.value) {
		const k = keyLabel(e);
		if (!m.has(k)) m.set(k, { key: k, total: 0, count: 0, entries: [] });
		const g = m.get(k);
		g.total += Number(e.amount) || 0;
		g.count += 1;
		g.entries.push(e);
	}
	return [...m.values()].sort((a, b) => b.total - a.total);
});
const grandTotal = computed(() => filtered.value.reduce((a, e) => a + (Number(e.amount) || 0), 0));

const groupLabel = computed(() => GROUPINGS.find((g) => g.key === groupBy.value).label);
const isImage = (url) => /\.(png|jpe?g|gif|webp|bmp|svg)(\?|$)/i.test(url || "");
function toggle(k) {
	expanded.value = expanded.value === k ? null : k;
}
</script>

<template>
	<DeskPage title="Expense Summary" :breadcrumbs="breadcrumbs" printable>
		<div v-if="loading" class="text-sm text-ink-500 italic py-10 text-center">Loading…</div>
		<div v-else-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<div v-else class="space-y-4">
			<ReportFilters
				:active="anyFilter"
				:shown="filtered.length"
				:total="all.length"
				noun="expenses"
				@clear="clearFilters"
			>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Find</span
					>
					<DeskInput v-model="f.q" placeholder="Description or id…" class="!w-48" />
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Project</span
					>
					<span class="w-48 inline-block">
						<DeskSearchableSelect
							v-model="f.project"
							:options="projectOptions"
							allow-clear
							placeholder="All projects"
							search-placeholder="Search…"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Account</span
					>
					<span class="w-52 inline-block">
						<DeskSearchableSelect
							v-model="f.account"
							:options="accountOptions"
							allow-clear
							placeholder="All accounts"
							search-placeholder="Search…"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Paid from</span
					>
					<span class="w-44 inline-block">
						<DeskSearchableSelect
							v-model="f.source"
							:options="sourceOptions"
							allow-clear
							placeholder="Any source"
							search-placeholder="Search…"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Person</span
					>
					<span class="w-44 inline-block">
						<DeskSearchableSelect
							v-model="f.holder"
							:options="holderOptions"
							allow-clear
							placeholder="Anyone"
							search-placeholder="Search…"
						/>
					</span>
				</label>
			</ReportFilters>

			<!-- Controls -->
			<div class="flex items-center gap-3 flex-wrap">
				<div class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Group by</span
					>
					<select
						v-model="groupBy"
						class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
					>
						<option v-for="g in GROUPINGS" :key="g.key" :value="g.key">
							{{ g.label }}
						</option>
					</select>
				</div>
				<div class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>From</span
					>
					<DeskInput v-model="from" type="date" class="!w-36" />
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>To</span
					>
					<DeskInput v-model="to" type="date" class="!w-36" />
				</div>
				<div class="ml-auto text-sm">
					<span class="text-ink-500">Total</span>
					<span class="font-semibold text-ink-900 tabular-nums">
						{{ fmtINR(grandTotal) }}</span
					>
				</div>
			</div>

			<div class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<table v-if="groups.length" class="w-full text-xs">
					<thead
						class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200 bg-ink-50"
					>
						<tr>
							<th class="text-left px-4 py-2">{{ groupLabel }}</th>
							<th class="text-right px-4 py-2">Entries</th>
							<th class="text-right px-4 py-2">Total</th>
							<th class="px-4 py-2"></th>
						</tr>
					</thead>
					<tbody>
						<template v-for="g in groups" :key="g.key">
							<tr
								class="border-b border-ink-100 hover:bg-brand-50/30 cursor-pointer"
								@click="toggle(g.key)"
							>
								<td class="px-4 py-2.5 text-ink-900">{{ g.key }}</td>
								<td class="px-4 py-2.5 text-right tabular-nums text-ink-500">
									{{ g.count }}
								</td>
								<td
									class="px-4 py-2.5 text-right tabular-nums font-medium text-ink-900"
								>
									{{ fmtINR(g.total) }}
								</td>
								<td class="px-4 py-2.5 text-right text-ink-400">
									{{ expanded === g.key ? "▾" : "▸" }}
								</td>
							</tr>
							<tr v-if="expanded === g.key" :key="g.key + '-d'">
								<td colspan="4" class="px-4 py-3 bg-ink-50/50">
									<div
										v-for="e in g.entries"
										:key="e.name"
										class="flex items-start justify-between gap-3 text-[11px] py-1 border-b border-ink-100 last:border-0"
									>
										<div class="flex items-start gap-2 min-w-0">
											<a
												v-if="e.attachment"
												:href="e.attachment"
												target="_blank"
												rel="noopener"
												class="flex-shrink-0"
											>
												<img
													v-if="isImage(e.attachment)"
													:src="e.attachment"
													class="w-8 h-8 object-cover rounded border border-ink-200"
												/>
												<span
													v-else
													class="w-8 h-8 flex items-center justify-center rounded border border-ink-200 bg-white text-ink-400"
													>📎</span
												>
											</a>
											<div class="min-w-0">
												<div class="text-ink-800">{{ e.description }}</div>
												<div class="text-ink-400">
													{{ fmtDate(e.date) }} · {{ e.source || "—" }} ·
													{{ projectName(e) }}
												</div>
											</div>
										</div>
										<span class="tabular-nums text-ink-900 flex-shrink-0">{{
											fmtINR(e.amount)
										}}</span>
									</div>
								</td>
							</tr>
						</template>
					</tbody>
				</table>
				<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
					No submitted expenses in this period.
				</div>
			</div>
		</div>
	</DeskPage>
</template>
