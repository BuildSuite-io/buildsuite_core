<script setup>
// Machinery Usage Log — the Machinery Utilisation report (Equipment workspace). Plant usage +
// cost by machine / project / cost code, with the prototype's filter strip (machine, project,
// period). Rows come resolved from the server (machine / project names, cost code + total cost) so
// nothing is looked up a second time on the client — see ISS-142.

import { computed, onMounted, reactive, ref, watch } from "vue";
import { useDataStore } from "@/stores";
import { useRoute, RouterLink } from "vue-router";

import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { usePermissions } from "@/composables/usePermissions";
import { getMachineryUsageReport } from "@/data/equipmentApi";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const route = useRoute();
const store = useDataStore();
const { canCreate } = usePermissions();

const all = ref([]);
const loading = ref(true);
const error = ref("");

async function load() {
	loading.value = true;
	try {
		all.value = (await getMachineryUsageReport()) || [];
	} catch (e) {
		error.value = e.message || __("Failed to load the usage log.");
	} finally {
		loading.value = false;
	}
}
onMounted(load);
// Re-scope to the topbar switcher's working company.
watch(() => store.activeCompany, load);

const search = ref("");
const BLANK = { machine: "", project: "", from: "", to: "" };
const f = reactive({ ...BLANK });
const anyFilter = computed(
	() => Object.keys(BLANK).some((k) => f[k] !== BLANK[k]) || !!search.value
);
function clearFilters() {
	Object.assign(f, BLANK);
	search.value = "";
}

// Machine + project pickers are built from the entries themselves, so no option offers a value
// with nothing behind it.
const machineOptions = computed(() => {
	const m = new Map();
	for (const u of all.value) if (u.machine) m.set(u.machine, u.machine_name || u.machine);
	return [...m.entries()]
		.map(([value, label]) => ({ value, label }))
		.sort((a, b) => a.label.localeCompare(b.label));
});
const projectOptions = computed(() => {
	const m = new Map();
	for (const u of all.value) if (u.project) m.set(u.project, u.project_name || u.project);
	return [...m.entries()]
		.map(([value, label]) => ({ value, label }))
		.sort((a, b) => a.label.localeCompare(b.label));
});

const rows = computed(() => {
	const t = search.value.trim().toLowerCase();
	return all.value.filter(
		(u) =>
			(!f.machine || u.machine === f.machine) &&
			(!f.project || u.project === f.project) &&
			(!f.from || (u.date || "") >= f.from) &&
			(!f.to || (u.date || "") <= f.to) &&
			(!t ||
				(u.machine_name || "").toLowerCase().includes(t) ||
				(u.project_name || "").toLowerCase().includes(t) ||
				(u.cost_code_label || u.task_subject || "").toLowerCase().includes(t))
	);
});

const columns = [
	{ key: "date", label: __("Date") },
	{ key: "machine", label: __("Machine") },
	{ key: "project", label: __("Project") },
	{ key: "cost_code", label: __("Cost code") },
	{ key: "quantity", label: __("Qty"), align: "right" },
	{ key: "total", label: __("Total cost"), align: "right" },
	{ key: "status", label: __("Status") },
];
const statusLabel = (s) => (s === 1 ? __("Submitted") : s === 2 ? __("Cancelled") : __("Draft"));

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Equipment"), to: "/equipment" },
	{ label: __("Machinery Usage") },
];

// Row click opens a read-only summary modal (as in the prototype); editing and the
// submit / cancel lifecycle stay on the full record, linked from the modal footer.
const detailId = ref(route.query.open ? String(route.query.open) : null);
const detail = computed(() => all.value.find((u) => u.name === detailId.value) || null);
function onRowClick(row) {
	detailId.value = row.name;
}
function closeDetail() {
	detailId.value = null;
}
const unitLabel = (unit) => (unit || "").replace(/s$/, "");
</script>

<template>
	<DeskPage :title="__('Machinery Usage Log')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink
				v-if="canCreate('machineryUsage')"
				to="/machinery-usage/new"
				class="desk-save-btn"
				>+ {{ __("Log usage") }}</RouterLink
			>
		</template>

		<div v-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<template v-else>
			<ReportFilters
				:active="anyFilter"
				:shown="rows.length"
				:total="all.length"
				noun="entries"
				@clear="clearFilters"
			>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Machine")
					}}</span>
					<span class="w-48 inline-block">
						<DeskSearchableSelect
							v-model="f.machine"
							:options="machineOptions"
							allow-clear
							:placeholder="__('All machines')"
							:search-placeholder="__('Search…')"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Project")
					}}</span>
					<span class="w-52 inline-block">
						<DeskSearchableSelect
							v-model="f.project"
							:options="projectOptions"
							allow-clear
							:placeholder="__('All projects')"
							:search-placeholder="__('Search…')"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Used")
					}}</span>
					<DeskInput v-model="f.from" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">{{ __("to") }}</span>
					<DeskInput v-model="f.to" type="date" class="!w-36" />
				</label>
			</ReportFilters>

			<DeskList
				filter-doctype="Machinery Usage"
				v-model="search"
				:rows="rows"
				:columns="columns"
				row-key="name"
				:search-placeholder="__('Search usage…')"
				@row-click="onRowClick"
			>
				<template #cell-date="{ row }">
					<span class="text-ink-500">{{ fmtDate(row.date) }}</span>
				</template>
				<template #cell-machine="{ row }">
					<DeskLink :to="`/machinery/${row.machine}`" @click.stop>{{
						row.machine_name
					}}</DeskLink>
				</template>
				<template #cell-project="{ row }">
					<span class="text-ink-700">{{ row.project_name || "—" }}</span>
				</template>
				<template #cell-cost_code="{ row }">
					<span v-if="row.cost_code_label" class="text-ink-700">{{
						row.cost_code_label
					}}</span>
					<span v-else class="italic text-ink-500">{{ __("Not coded") }}</span>
				</template>
				<template #cell-quantity="{ row }">
					<span class="tabular-nums">{{ row.quantity }} {{ row.unit }}</span>
				</template>
				<template #cell-status="{ row }">
					<span class="text-ink-700">{{ statusLabel(row.docstatus) }}</span>
				</template>
				<template #cell-total="{ row }">
					<span class="tabular-nums text-ink-900 font-medium">{{
						fmtINR(row.total)
					}}</span>
				</template>

				<template #empty>
					<div class="text-sm text-ink-500">
						{{ loading ? __("Loading usage log…") : __("No usage logged yet.") }}
						<RouterLink
							v-if="!loading && canCreate('machineryUsage')"
							to="/machinery-usage/new"
							class="desk-link"
							>{{ __("Log usage →") }}</RouterLink
						>
					</div>
				</template>
			</DeskList>
		</template>

		<Teleport to="body">
			<div
				v-if="detail"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6"
				@click.self="closeDetail"
				@keydown.esc="closeDetail"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-lg shadow-fp-lg rounded-xl flex flex-col"
					style="max-height: 88vh"
					@click.stop
				>
					<header
						class="px-4 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0"
					>
						<div class="flex items-center gap-2 min-w-0">
							<h2 class="text-sm font-semibold text-ink-900 truncate">
								{{ detail.machine_name }}
							</h2>
							<span
								class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600 rounded-full font-mono"
								>{{ detail.name }}</span
							>
							<span class="text-[10px] text-ink-500">{{
								statusLabel(detail.docstatus)
							}}</span>
						</div>
						<button
							type="button"
							class="text-ink-400 hover:text-ink-900 flex-shrink-0"
							@click="closeDetail"
						>
							✕
						</button>
					</header>

					<div class="px-4 py-4 overflow-y-auto flex-1 space-y-4">
						<div
							class="flex items-center justify-between bg-ink-50 rounded-lg px-4 py-3"
						>
							<div
								class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
							>
								{{ __("Total cost") }}
							</div>
							<div class="text-xl font-semibold text-ink-900 tabular-nums">
								{{ fmtINR(detail.total) }}
							</div>
						</div>

						<div class="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
							<div>
								<div
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
								>
									{{ __("Date") }}
								</div>
								<div class="text-ink-900 mt-0.5">{{ fmtDate(detail.date) }}</div>
							</div>
							<div>
								<div
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
								>
									{{ __("Machine") }}
								</div>
								<div class="mt-0.5">
									<DeskLink :to="`/machinery/${detail.machine}`">{{
										detail.machine_name
									}}</DeskLink>
								</div>
							</div>
							<div>
								<div
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
								>
									{{ __("Project") }}
								</div>
								<div class="text-ink-900 mt-0.5">
									{{ detail.project_name || "—" }}
								</div>
							</div>
							<div>
								<div
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
								>
									{{ __("Cost code") }}
								</div>
								<div
									class="mt-0.5"
									:class="
										detail.cost_code_label
											? 'text-ink-900'
											: 'text-ink-400 italic'
									"
								>
									{{ detail.cost_code_label || __("Not coded") }}
								</div>
							</div>
							<div>
								<div
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
								>
									{{ __("Quantity") }}
								</div>
								<div class="text-ink-900 mt-0.5 tabular-nums">
									{{ detail.quantity }} {{ detail.unit }}
								</div>
							</div>
							<div>
								<div
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
								>
									{{ __("Rate") }}
								</div>
								<div class="text-ink-900 mt-0.5 tabular-nums">
									{{ fmtINR(detail.rate) }} / {{ unitLabel(detail.unit) }}
								</div>
							</div>
						</div>

						<div class="bg-ink-50 rounded-lg px-4 py-3 text-sm space-y-1">
							<div class="flex justify-between text-ink-600">
								<span
									>{{ __("Usage") }} ({{ detail.quantity }} {{ detail.unit }} ×
									{{ fmtINR(detail.rate) }})</span
								>
								<span class="tabular-nums">{{
									fmtINR((detail.quantity || 0) * (detail.rate || 0))
								}}</span>
							</div>
							<div class="flex justify-between text-ink-600">
								<span>{{ __("Fuel") }}</span>
								<span class="tabular-nums">{{
									detail.fuel_cost ? fmtINR(detail.fuel_cost) : "—"
								}}</span>
							</div>
							<div
								class="flex justify-between font-semibold text-ink-900 border-t border-ink-200 pt-1.5"
							>
								<span>{{ __("Total") }}</span>
								<span class="tabular-nums">{{ fmtINR(detail.total) }}</span>
							</div>
						</div>

						<div
							class="text-[11px]"
							:class="
								detail.docstatus === 1 && detail.cost_code_label
									? 'text-ink-500'
									: 'text-warning-700'
							"
						>
							{{
								detail.docstatus !== 1
									? __(
											"Not submitted yet, so this cost is not posted to the estimate."
									  )
									: detail.cost_code_label
									? __(
											"This cost is posted to the estimate's Actual at its cost code."
									  )
									: __(
											"Not cost-coded, so this cost does not reach the estimate."
									  )
							}}
						</div>
					</div>

					<footer
						class="px-4 py-3 border-t border-ink-200 flex items-center justify-between gap-2 flex-shrink-0"
					>
						<RouterLink
							:to="`/machinery-usage/${detail.name}`"
							class="desk-link text-xs"
							>{{ __("Open full record →") }}</RouterLink
						>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
							@click="closeDetail"
						>
							{{ __("Close") }}
						</button>
					</footer>
				</div>
			</div>
		</Teleport>
	</DeskPage>
</template>
