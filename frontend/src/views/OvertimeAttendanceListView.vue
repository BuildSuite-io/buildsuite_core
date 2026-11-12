<script setup>
// Overtime Attendance Register — read-only. Rows are generated when a Field
// Attendance sheet carrying overtime hours is submitted. Filters (project, worker,
// date range) + a Total-OT-hours / Total-amount subtitle mirror the prototype. Cost code is what
// posts the overtime wage to the BOQ Actual.

import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";
import { frappeRequest } from "frappe-ui-frappe-request";

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
// The search box lives in the list; its text and counts come back through events so the subtitle
// and the "N of M rows" line follow it.
const search = ref("");
const shown = ref(null);
const everything = ref(null);
const SEARCH_FIELDS = ["employee_name", "name", "project_name", "cost_code_label"];
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
function currentSearchFilters() {
	const term = search.value.trim();
	return term ? SEARCH_FIELDS.map((f) => [f, "like", `%${term}%`]) : [];
}
async function loadTotals() {
	const filters = JSON.stringify(currentServerFilters());
	const or_filters = JSON.stringify(currentSearchFilters());
	const total = (field) =>
		frappeRequest({
			url: "buildsuite_core.api.field_attendance.register_total",
			params: { doctype: "Overtime Attendance Register", field, filters, or_filters },
		});
	try {
		const [hours, amount] = await Promise.all([
			total("overtime_hours"),
			total("overtime_wage_calculated"),
		]);
		totalHours.value = Number(hours) || 0;
		totalAmount.value = Number(amount) || 0;
	} catch {
		totalHours.value = 0;
		totalAmount.value = 0;
	}
}
let totalTimer = null;
watch(
	[filterValues, search],
	() => {
		clearTimeout(totalTimer);
		totalTimer = setTimeout(loadTotals, 250);
	},
	{ immediate: true, deep: true }
);
// Rows before any filter, for "N of M rows".
frappeRequest({
	url: "frappe.client.get_count",
	params: {
		doctype: "Overtime Attendance Register",
		filters: JSON.stringify([["docstatus", "<", 2]]),
	},
})
	.then((n) => (everything.value = Number(n) || 0))
	.catch(() => {});

const subtitle = computed(() =>
	__("{0} OT hrs · {1}", [totalHours.value, fmtINR(totalAmount.value)])
);

const columns = [
	{ key: "overtime_date", label: __("Date") },
	{ key: "employee_name", label: __("Worker") },
	{
		key: "source",
		label: __("Captured as"),
		fields: ["source", "timesheet", "field_attendance"],
	},
	{ key: "project", label: __("Project") },
	{
		key: "cost_code_label",
		label: __("Cost code"),
		fields: ["cost_code_label", "cost_code_item", "cost_code_group"],
	},
	{ key: "overtime_hours", label: __("OT hrs"), align: "right" },
	{ key: "overtime_rate", label: __("OT rate"), align: "right" },
	{ key: "overtime_wage_calculated", label: __("OT wage"), align: "right" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Overtime Attendance Register") },
];
</script>

<template>
	<DeskPage
		:title="__('Overtime Attendance Register')"
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
					__("Date")
				}}</span>
				<DeskInput v-model="fromFilter" type="date" class="!w-36" />
				<span class="text-[11px] text-ink-400">{{ __("to") }}</span>
				<DeskInput v-model="toFilter" type="date" class="!w-36" />
			</label>
		</ReportFilters>

		<DocTypeListView
			doctype="Overtime Attendance Register"
			@total-change="(n) => (shown = n)"
			@search-change="(v) => (search = v)"
			:field-order="[
				'overtime_date',
				'employee_name',
				'source',
				'timesheet',
				'field_attendance',
				'project',
				'overtime_hours',
				'overtime_rate',
				'overtime_wage_calculated',
			]"
			:columns="columns"
			:search-fields="SEARCH_FIELDS"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			:base-filters="[['docstatus', '<', 2]]"
			cache-key="buildsuite-overtime-attendance"
			row-key="name"
			initial-order-by="overtime_date desc"
			:search-placeholder="__('Search worker / project / cost code…')"
			:empty-message="__('No overtime yet — submit a Field Attendance with overtime hours.')"
		>
			<template #cell-overtime_date="{ row }">
				{{ fmtDate(row.overtime_date) }}
			</template>

			<template #cell-employee_name="{ row }">
				<span class="text-ink-900 font-medium">{{
					row.employee_name || row.employee
				}}</span>
				<span class="text-ink-400 text-[11px]"> {{ row.employee }}</span>
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

			<template #cell-overtime_hours="{ row }">
				<span class="tabular-nums">{{ row.overtime_hours }}</span>
			</template>

			<template #cell-overtime_rate="{ row }">
				<span class="tabular-nums">{{ fmtINR(row.overtime_rate) }}</span>
			</template>

			<template #cell-overtime_wage_calculated="{ row }">
				<span class="tabular-nums font-medium">{{
					fmtINR(row.overtime_wage_calculated)
				}}</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
