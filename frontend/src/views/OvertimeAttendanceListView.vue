<script setup>
// Overtime Attendance Register — read-only. Rows are generated when a Field
// Attendance sheet carrying overtime hours is submitted. Filters (project, worker,
// date range) + a Total-OT-hours / Total-amount subtitle mirror the prototype.

import { computed, ref, watch } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { fmtDate, fmtINR } from "@/utils/format";

const { projectOptions, projectLabel } = useProjectOptions();
const { workerOptions } = useFieldEmployeeOptions();

const projectFilter = ref("");
const workerFilter = ref("");
const fromFilter = ref("");
const toFilter = ref("");

const filterValues = computed(() => ({
	project: projectFilter.value,
	worker: workerFilter.value,
	from: fromFilter.value,
	to: toFilter.value,
}));
const filterFieldMap = {
	project: "project",
	worker: "employee",
	from: { field: "overtime_date", op: ">=" },
	to: { field: "overtime_date", op: "<=" },
};

const anyFilter = computed(() => Object.values(filterValues.value).some((v) => v));
function clearFilters() {
	projectFilter.value = "";
	workerFilter.value = "";
	fromFilter.value = "";
	toFilter.value = "";
}

// Totals across the WHOLE filtered set — a single SQL sum with the same filters.
const totalHours = ref(0);
const totalAmount = ref(0);
function currentServerFilters() {
	const f = [["docstatus", "<", 2]];
	if (projectFilter.value) f.push(["project", "=", projectFilter.value]);
	if (workerFilter.value) f.push(["employee", "=", workerFilter.value]);
	if (fromFilter.value) f.push(["overtime_date", ">=", fromFilter.value]);
	if (toFilter.value) f.push(["overtime_date", "<=", toFilter.value]);
	return f;
}
async function loadTotals() {
	try {
		const params = new URLSearchParams({
			doctype: "Overtime Attendance Register",
			fields: JSON.stringify([
				"sum(overtime_hours) as hours",
				"sum(overtime_wage_calculated) as amount",
			]),
			filters: JSON.stringify(currentServerFilters()),
		});
		const res = await fetch("/api/method/frappe.client.get_list?" + params, {
			credentials: "include",
			headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		});
		const data = await res.json();
		totalHours.value = Number(data?.message?.[0]?.hours) || 0;
		totalAmount.value = Number(data?.message?.[0]?.amount) || 0;
	} catch {
		totalHours.value = 0;
		totalAmount.value = 0;
	}
}
watch(filterValues, loadTotals, { immediate: true, deep: true });

const subtitle = computed(
	() => `Total OT hours ${totalHours.value} · Total amount ${fmtINR(totalAmount.value)}`
);

const columns = [
	{ key: "overtime_date", label: "Date" },
	{ key: "employee_name", label: "Worker" },
	{ key: "task", label: "Task" },
	{ key: "project", label: "Project" },
	{ key: "overtime_hours", label: "OT hrs", align: "right" },
	{ key: "overtime_rate", label: "OT rate", align: "right" },
	{ key: "overtime_wage_calculated", label: "OT wage", align: "right" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Overtime Attendance Register" },
];
</script>

<template>
	<DeskPage title="Overtime Attendance Register" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<DocTypeListView
			doctype="Overtime Attendance Register"
			:field-order="[
				'overtime_date',
				'employee_name',
				'task',
				'task_subject',
				'project',
				'overtime_hours',
				'overtime_rate',
				'overtime_wage_calculated',
			]"
			:columns="columns"
			:search-fields="['employee_name', 'name', 'project']"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			:base-filters="[['docstatus', '<', 2]]"
			cache-key="buildsuite-overtime-attendance"
			row-key="name"
			initial-order-by="overtime_date desc"
			search-placeholder="Search worker / project…"
			empty-message="No overtime yet — submit a Field Attendance with overtime hours."
		>
			<template #filter-chips>
				<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
					<div class="w-48">
						<DeskSearchableSelect
							v-model="projectFilter"
							:options="projectOptions"
							placeholder="All projects"
							search-placeholder="Search projects…"
							allow-clear
						/>
					</div>
					<div class="w-48">
						<DeskSearchableSelect
							v-model="workerFilter"
							:options="workerOptions"
							placeholder="Everyone"
							search-placeholder="Search workers…"
							allow-clear
						/>
					</div>
					<div class="flex items-center gap-1.5">
						<DeskInput v-model="fromFilter" type="date" class="!w-36" />
						<span class="text-[11px] text-ink-400">to</span>
						<DeskInput v-model="toFilter" type="date" class="!w-36" />
					</div>
					<button
						v-if="anyFilter"
						type="button"
						class="text-[11px] text-ink-500 hover:text-ink-800 px-1"
						@click="clearFilters"
					>
						Clear
					</button>
				</div>
			</template>

			<template #cell-overtime_date="{ row }">
				<span class="text-ink-700">{{ fmtDate(row.overtime_date) || "—" }}</span>
			</template>

			<template #cell-employee_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.employee_name || row.employee }}</span>
			</template>

			<template #cell-task="{ row }">
				<span class="text-ink-700">{{ row.task_subject || row.task || "—" }}</span>
			</template>

			<template #cell-project="{ row }">
				<DeskLink v-if="row.project" :to="`/projects/${row.project}`" @click.stop>
					{{ projectLabel(row.project) }}
				</DeskLink>
				<span v-else class="text-ink-400">—</span>
			</template>

			<template #cell-overtime_hours="{ row }">
				<span class="tabular-nums text-ink-700">{{ row.overtime_hours || 0 }}</span>
			</template>

			<template #cell-overtime_rate="{ row }">
				<span class="tabular-nums text-ink-700">
					{{ row.overtime_rate ? fmtINR(row.overtime_rate) : "—" }}
				</span>
			</template>

			<template #cell-overtime_wage_calculated="{ row }">
				<span class="tabular-nums text-ink-900 font-medium">
					{{ row.overtime_wage_calculated ? fmtINR(row.overtime_wage_calculated) : "—" }}
				</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
