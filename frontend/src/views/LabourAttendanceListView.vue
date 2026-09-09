<script setup>
// Labour Attendance Register — read-only. Rows are generated when a Field
// Attendance sheet is submitted, never created by hand here. Filters (project,
// worker, status, date range) + a total-daily-wages subtitle mirror the prototype
// (S216). Task/Day-Type columns need source data on the register doctype.

import { computed, ref, watch } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { fmtDate, fmtINR } from "@/utils/format";

const { projectOptions, projectLabel } = useProjectOptions();
const { workerOptions } = useFieldEmployeeOptions();

const STATUSES = ["Full Day", "Half Day", "Absent"];

const projectFilter = ref("");
const workerFilter = ref("");
const statusFilter = ref("");
const fromFilter = ref("");
const toFilter = ref("");

const filterValues = computed(() => ({
	project: projectFilter.value,
	worker: workerFilter.value,
	status: statusFilter.value,
	from: fromFilter.value,
	to: toFilter.value,
}));
// worker → the employee link; the date range targets attendance_date via op.
const filterFieldMap = {
	project: "project",
	worker: "employee",
	status: "status",
	from: { field: "attendance_date", op: ">=" },
	to: { field: "attendance_date", op: "<=" },
};

const anyFilter = computed(() =>
	Object.values(filterValues.value).some((v) => v)
);
function clearFilters() {
	projectFilter.value = "";
	workerFilter.value = "";
	statusFilter.value = "";
	fromFilter.value = "";
	toFilter.value = "";
}

// Total daily wages across the WHOLE filtered set (not just the visible page) —
// a single SQL sum with the same filters, shown as the page subtitle.
const totalWages = ref(0);
function currentServerFilters() {
	const f = [["docstatus", "<", 2]];
	if (projectFilter.value) f.push(["project", "=", projectFilter.value]);
	if (workerFilter.value) f.push(["employee", "=", workerFilter.value]);
	if (statusFilter.value) f.push(["status", "=", statusFilter.value]);
	if (fromFilter.value) f.push(["attendance_date", ">=", fromFilter.value]);
	if (toFilter.value) f.push(["attendance_date", "<=", toFilter.value]);
	return f;
}
async function loadTotal() {
	try {
		const params = new URLSearchParams({
			doctype: "Labour Attendance Register",
			fields: JSON.stringify(["sum(daily_wage_calculated) as total"]),
			filters: JSON.stringify(currentServerFilters()),
		});
		const res = await fetch("/api/method/frappe.client.get_list?" + params, {
			credentials: "include",
			headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		});
		const data = await res.json();
		totalWages.value = Number(data?.message?.[0]?.total) || 0;
	} catch {
		totalWages.value = 0;
	}
}
watch(filterValues, loadTotal, { immediate: true, deep: true });

const subtitle = computed(() => `Total daily wages ${fmtINR(totalWages.value)}`);

const columns = [
	{ key: "attendance_date", label: "Date" },
	{ key: "employee_name", label: "Worker" },
	{ key: "status", label: "Status" },
	{ key: "project", label: "Project" },
	{ key: "wage_rate", label: "Wage rate", align: "right" },
	{ key: "daily_wage_calculated", label: "Daily wage", align: "right" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Labour Attendance Register" },
];
</script>

<template>
	<DeskPage title="Labour Attendance Register" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<DocTypeListView
			doctype="Labour Attendance Register"
			:field-order="[
				'attendance_date',
				'employee_name',
				'status',
				'project',
				'wage_rate',
				'daily_wage_calculated',
			]"
			:columns="columns"
			:search-fields="['employee_name', 'name', 'project']"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			:base-filters="[['docstatus', '<', 2]]"
			cache-key="buildsuite-labour-attendance"
			row-key="name"
			initial-order-by="attendance_date desc"
			search-placeholder="Search worker / project…"
			empty-message="No labour attendance yet — submit a Field Attendance."
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
					<DeskSelect v-model="statusFilter" class="!w-32">
						<option value="">Any status</option>
						<option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
					</DeskSelect>
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

			<template #cell-attendance_date="{ row }">
				<span class="text-ink-700">{{ fmtDate(row.attendance_date) || "—" }}</span>
			</template>

			<template #cell-employee_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.employee_name || row.employee }}</span>
			</template>

			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>

			<template #cell-project="{ row }">
				<DeskLink v-if="row.project" :to="`/projects/${row.project}`" @click.stop>
					{{ projectLabel(row.project) }}
				</DeskLink>
				<span v-else class="text-ink-400">—</span>
			</template>

			<template #cell-wage_rate="{ row }">
				<span class="tabular-nums text-ink-700">
					{{ row.wage_rate ? fmtINR(row.wage_rate) : "—" }}
				</span>
			</template>

			<template #cell-daily_wage_calculated="{ row }">
				<span class="tabular-nums text-ink-900 font-medium">
					{{ row.daily_wage_calculated ? fmtINR(row.daily_wage_calculated) : "—" }}
				</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
