<script setup>
// Cost vs Budget by Cost Code — the project cost-control report, launched from the project
// overview (?project=). Per BOQ cost code, grouped by cost type: Planned (Approved BOQ),
// Committed (submitted subcontractor work orders) and Actual (recognised spend across every
// rail), with Variance = Actual − Planned. The server computes the full set
// (buildsuite_core.api.cost_report); the filters here narrow it client-side (variance
// threshold, cost type, search) with a live "N of M" count.
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getCostVsBudget } from "@/data/costReportApi";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { fmtINR, fmtCompactINR } from "@/utils/format";

const route = useRoute();
const router = useRouter();

const projectId = ref(route.query.project || "");
const loading = ref(false);
const rows = ref([]); // flat rows from the server
const boq = ref(null); // the Approved BOQ name, or null when there is none

// --- filters (client-side, over the loaded set) ---
const BLANK = { q: "", costType: "" };
const f = reactive({ ...BLANK });
const varianceThreshold = ref("0"); // % — doubles as the overrun filter
function clearFilters() {
	Object.assign(f, BLANK);
	varianceThreshold.value = "0";
}
const anyFilter = computed(
	() => f.q !== "" || f.costType !== "" || varianceThreshold.value !== "0"
);
const hit = (hay, needle) =>
	!needle ||
	String(hay || "")
		.toLowerCase()
		.includes(needle.trim().toLowerCase());

// Cost types present on this project, so the picker never offers an empty one.
const costTypeOptions = computed(() =>
	[...new Set(rows.value.map((r) => r.costType))].sort().map((v) => ({ value: v, label: v }))
);

// Threshold-filtered, grouped by cost type. Kept separate from the search/type filter below so
// the bar can report "N of M" and the Total line stay honest about the threshold set.
const grouped = computed(() => {
	const t = Number(varianceThreshold.value) || 0;
	const kept = t > 0 ? rows.value.filter((r) => r.variancePct >= t) : rows.value;
	const byType = {};
	for (const r of kept) (byType[r.costType] ||= []).push(r);
	return Object.entries(byType)
		.sort((a, b) => a[0].localeCompare(b[0]))
		.map(([type, list]) => ({
			type,
			rows: list,
			planned: list.reduce((a, r) => a + r.planned, 0),
			committed: list.reduce((a, r) => a + r.committed, 0),
			actual: list.reduce((a, r) => a + r.actual, 0),
		}));
});
// What actually renders — the threshold set narrowed by cost type + search.
const costGroups = computed(() => {
	if (!f.costType && !f.q) return grouped.value;
	return grouped.value
		.filter((g) => !f.costType || g.type === f.costType)
		.map((g) => ({ ...g, rows: g.rows.filter((r) => hit(r.code, f.q) || hit(r.name, f.q)) }))
		.filter((g) => g.rows.length);
});
const shownCount = computed(() => costGroups.value.reduce((a, g) => a + g.rows.length, 0));
// Total reflects the threshold set (not the search) — the same convention as the prototype.
const totals = computed(() =>
	grouped.value.reduce(
		(a, g) => ({
			planned: a.planned + g.planned,
			committed: a.committed + g.committed,
			actual: a.actual + g.actual,
		}),
		{ planned: 0, committed: 0, actual: 0 }
	)
);

// Over budget (actual > planned) reads red; under reads green.
function tone(v) {
	return v > 0 ? "text-danger-700" : v < 0 ? "text-success-700" : "text-ink-500";
}

async function load(pid) {
	if (!pid) {
		rows.value = [];
		boq.value = null;
		return;
	}
	loading.value = true;
	try {
		const res = (await getCostVsBudget(pid)) || {};
		rows.value = res.rows || [];
		boq.value = res.boq || null;
	} catch (err) {
		showToast(err.message || "Failed to load Cost vs Budget", "error");
		rows.value = [];
		boq.value = null;
	} finally {
		loading.value = false;
	}
}
watch(projectId, (id) => {
	clearFilters(); // a filter from the previous project shouldn't leak onto the next
	router.replace({ path: route.path, query: { ...route.query, project: id || undefined } });
	load(id);
});
load(projectId.value);

function printReport() {
	window.print();
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Cost vs Budget by Cost Code" },
];
</script>

<template>
	<DeskPage title="Cost vs Budget by Cost Code" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="printReport"
			>
				Print
			</button>
		</template>

		<p class="text-xs text-ink-500 mb-3">
			Planned, committed, actual and variance per cost code, grouped by cost type.
		</p>

		<!-- Scope + filters -->
		<ReportFilters
			:active="anyFilter"
			:shown="shownCount"
			:total="rows.length"
			noun="cost codes"
			@clear="clearFilters"
		>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
					>Project</span
				>
				<span class="w-56 inline-block">
					<DeskLinkPicker
						v-model="projectId"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'name']"
						placeholder="Pick a project…"
					/>
				</span>
			</label>

			<template v-if="projectId">
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Find</span
					>
					<DeskInput v-model="f.q" placeholder="Code or description…" class="!w-52" />
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Cost type</span
					>
					<span class="w-44 inline-block">
						<DeskSearchableSelect
							v-model="f.costType"
							:options="costTypeOptions"
							allow-clear
							placeholder="All types"
							search-placeholder="Search…"
						/>
					</span>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Variance over</span
					>
					<DeskSelect v-model="varianceThreshold" class="!w-24">
						<option value="0">All</option>
						<option value="5">5%</option>
						<option value="10">10%</option>
						<option value="20">20%</option>
					</DeskSelect>
				</label>
			</template>
		</ReportFilters>

		<div v-if="!projectId" class="text-sm text-ink-500 italic py-10 text-center">
			Pick a project to run this report.
		</div>

		<template v-else>
			<div v-if="!costGroups.length" class="text-sm text-ink-500 italic py-10 text-center">
				<template v-if="!boq"
					>No approved BOQ on this project — there is nothing to measure cost against
					yet.</template
				>
				<template v-else>No cost codes exceed the selected variance threshold.</template>
			</div>
			<div v-else class="space-y-4">
				<div
					v-for="g in costGroups"
					:key="g.type"
					class="bg-white border border-ink-200 rounded-lg overflow-hidden"
				>
					<div
						class="px-3 py-2 bg-ink-50 border-b border-ink-200 flex items-center justify-between"
					>
						<span class="text-[11px] font-semibold uppercase tracking-wider text-ink-700">{{
							g.type
						}}</span>
						<span class="text-[11px] text-ink-500 tabular-nums"
							>{{ fmtCompactINR(g.actual) }} of {{ fmtCompactINR(g.planned) }}</span
						>
					</div>
					<div class="overflow-x-auto">
						<table class="w-full text-xs">
							<thead class="text-ink-500 uppercase tracking-wider text-[10px]">
								<tr>
									<th class="text-left px-3 py-2">Cost code</th>
									<th class="text-right px-3 py-2">Planned</th>
									<th class="text-right px-3 py-2">Committed</th>
									<th class="text-right px-3 py-2">Actual</th>
									<th class="text-right px-3 py-2">Variance</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="r in g.rows" :key="r.key" class="border-t border-ink-100">
									<td class="px-3 py-2 text-ink-900">
										<span class="font-mono text-[11px] text-ink-500 mr-1.5">{{
											r.code
										}}</span
										>{{ r.name }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ fmtINR(r.planned) }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-info-700">
										{{ r.committed ? fmtINR(r.committed) : "—" }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-900">
										{{ fmtINR(r.actual) }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums" :class="tone(r.variance)">
										{{ r.variance > 0 ? "+" : "" }}{{ fmtINR(r.variance) }}
										<span class="text-[10px] ml-1"
											>({{ r.variancePct > 0 ? "+" : ""
											}}{{ r.variancePct.toFixed(0) }}%)</span
										>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
				<div
					class="bg-ink-50 border border-ink-200 rounded-lg px-3 py-2 flex items-center justify-between text-xs"
				>
					<span class="font-medium text-ink-900">Total</span>
					<span class="tabular-nums text-ink-700">
						Planned {{ fmtINR(totals.planned) }} · Committed
						{{ fmtINR(totals.committed) }} · Actual {{ fmtINR(totals.actual) }}
					</span>
				</div>
			</div>
		</template>
	</DeskPage>
</template>
