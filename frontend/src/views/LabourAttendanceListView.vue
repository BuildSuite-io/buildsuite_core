<script setup>
// Labour Attendance Register — read-only. Rows are generated when a Field
// Attendance sheet is submitted, never created by hand here. Filters (project,
// worker, status, date range) + a total-daily-wages subtitle mirror the prototype
// (S216). "Captured as" links to the sheet or timesheet the row came from; Hours is the regular
// hours over the full day the row was made with; Cost code is what posts the wage to the BOQ Actual.

import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";
import { frappeRequest } from "frappe-ui-frappe-request";

const { projectOptions, projectLabel } = useProjectOptions();
const { workerOptions } = useFieldEmployeeOptions();

const STATUSES = ["Full Day", "Half Day", "Absent", "Hours"];

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

const anyFilter = computed(() => Object.values(filterValues.value).some((v) => v));
// The search box lives in the list; its text and counts come back through events so the subtitle
// and the "N of M rows" line follow it.
const search = ref("");
const shown = ref(null);
const everything = ref(null);
const SEARCH_FIELDS = ["employee_name", "name", "project_name", "cost_code_label"];
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
function currentSearchFilters() {
	const term = search.value.trim();
	return term ? SEARCH_FIELDS.map((f) => [f, "like", `%${term}%`]) : [];
}
async function loadTotal() {
	try {
		totalWages.value =
			Number(
				await frappeRequest({
					url: "buildsuite_core.api.field_attendance.register_total",
					params: {
						doctype: "Labour Attendance Register",
						field: "daily_wage_calculated",
						filters: JSON.stringify(currentServerFilters()),
						or_filters: JSON.stringify(currentSearchFilters()),
					},
				})
			) || 0;
	} catch {
		totalWages.value = 0;
	}
}
let totalTimer = null;
watch(
	[filterValues, search],
	() => {
		clearTimeout(totalTimer);
		totalTimer = setTimeout(loadTotal, 250);
	},
	{ immediate: true, deep: true }
);
// Rows before any filter, for "N of M rows".
frappeRequest({
	url: "frappe.client.get_count",
	params: {
		doctype: "Labour Attendance Register",
		filters: JSON.stringify([["docstatus", "<", 2]]),
	},
})
	.then((n) => (everything.value = Number(n) || 0))
	.catch(() => {});

const subtitle = computed(() => __("Total wages {0}", [fmtINR(totalWages.value)]));

const columns = [
	{ key: "attendance_date", label: __("Date") },
	{ key: "employee_name", label: __("Worker") },
	{ key: "status", label: __("Status") },
	{
		key: "source",
		label: __("Captured as"),
		fields: ["source", "timesheet", "field_attendance"],
	},
	{
		key: "regular_hours",
		label: __("Hours"),
		align: "right",
		fields: ["regular_hours", "full_day_hours"],
	},
	{ key: "day_type", label: __("Day type") },
	{ key: "project", label: __("Project") },
	// Copied from the Field Attendance row (or the timesheet row); this is what posts the wage to
	// the BOQ Actual.
	{
		key: "cost_code_label",
		label: __("Cost code"),
		fields: ["cost_code_label", "cost_code_item", "cost_code_group"],
	},
	{ key: "wage_rate", label: __("Wage rate"), align: "right" },
	{ key: "daily_wage_calculated", label: __("Wage"), align: "right" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Labour Attendance Register") },
];
</script>

<template>
	<DeskPage
		:title="__('Labour Attendance Register')"
		:subtitle="subtitle"
		:breadcrumbs="breadcrumbs"
	>
		<ReportFilters
			:active="anyFilter"
			:shown="shown"
			:total="everything"
			noun="rows"
			@clear="clearFilters"
		>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
					__("Project")
				}}</span>
				<span class="w-52 inline-block"
					><DeskSearchableSelect
						v-model="projectFilter"
						:options="projectOptions"
						allow-clear
						:placeholder="__('All projects')"
						:search-placeholder="__('Search…')"
				/></span>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
					__("Worker")
				}}</span>
				<span class="w-48 inline-block"
					><DeskSearchableSelect
						v-model="workerFilter"
						:options="workerOptions"
						allow-clear
						:placeholder="__('Everyone')"
						:search-placeholder="__('Search…')"
				/></span>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
					__("Status")
				}}</span>
				<DeskSelect v-model="statusFilter" class="!w-32">
					<option value="">{{ __("Any") }}</option>
					<option v-for="s in STATUSES" :key="s" :value="s">{{ __(s) }}</option>
				</DeskSelect>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
					__("Date")
				}}</span>
				<DeskInput v-model="fromFilter" type="date" class="!w-36" />
				<span class="text-[11px] text-ink-400">{{ __("to") }}</span>
				<DeskInput v-model="toFilter" type="date" class="!w-36" />
			</label>
		</ReportFilters>

		<DocTypeListView
			doctype="Labour Attendance Register"
			@total-change="(n) => (shown = n)"
			@search-change="(v) => (search = v)"
			:field-order="[
				'attendance_date',
				'employee_name',
				'status',
				'source',
				'timesheet',
				'field_attendance',
				'regular_hours',
				'full_day_hours',
				'day_type',
				'project',
				'cost_code_label',
				'cost_code_item',
				'cost_code_group',
				'wage_rate',
				'daily_wage_calculated',
			]"
			:columns="columns"
			:search-fields="SEARCH_FIELDS"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			:base-filters="[['docstatus', '<', 2]]"
			cache-key="buildsuite-labour-attendance"
			row-key="name"
			initial-order-by="attendance_date desc"
			:search-placeholder="__('Search worker / project / cost code…')"
			:empty-message="__('No labour attendance yet — submit a Field Attendance.')"
		>
			<template #cell-attendance_date="{ row }">
				{{ fmtDate(row.attendance_date) }}
			</template>

			<template #cell-employee_name="{ row }">
				<span class="text-ink-900 font-medium">{{
					row.employee_name || row.employee
				}}</span>
				<span class="text-ink-400 text-[11px]"> {{ row.employee }}</span>
			</template>

			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" size="xs" />
			</template>

			<template #cell-source="{ row }">
				<RouterLink
					v-if="row.source === 'Timesheet' && row.timesheet"
					:to="`/timesheets/${encodeURIComponent(row.timesheet)}`"
					class="desk-link"
					@click.stop
					>{{ __("Timesheet") }}</RouterLink
				>
				<RouterLink
					v-else-if="row.field_attendance"
					:to="`/field-attendance/${encodeURIComponent(row.field_attendance)}`"
					class="desk-link"
					@click.stop
					>{{ __("Attendance") }}</RouterLink
				>
			</template>

			<template #cell-regular_hours="{ row }">
				<span class="tabular-nums text-ink-900"
					>{{ row.regular_hours || "—"
					}}<span v-if="row.full_day_hours" class="text-ink-400 text-[10px]">
						/ {{ row.full_day_hours }} h</span
					></span
				>
			</template>

			<template #cell-day_type="{ row }">
				<span class="text-ink-600">{{ row.day_type }}</span>
			</template>

			<template #cell-project="{ row }">
				<DeskLink v-if="row.project" :to="`/projects/${row.project}`" @click.stop>
					{{ projectLabel(row.project) }}
				</DeskLink>
			</template>

			<template #cell-cost_code_label="{ row }">
				<span
					v-if="row.cost_code_label || row.cost_code_item || row.cost_code_group"
					class="text-ink-700"
					>{{ row.cost_code_label || row.cost_code_item || row.cost_code_group }}</span
				>
				<span v-else class="text-ink-400 italic">{{ __("Not coded") }}</span>
			</template>

			<template #cell-wage_rate="{ row }">
				<span class="tabular-nums">{{ fmtINR(row.wage_rate) }}</span>
			</template>

			<template #cell-daily_wage_calculated="{ row }">
				<span class="tabular-nums font-medium">{{
					fmtINR(row.daily_wage_calculated)
				}}</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
