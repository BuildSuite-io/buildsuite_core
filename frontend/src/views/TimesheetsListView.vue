<script setup>
// Timesheets — one worker, one day, hours against a project and cost code. Read-only list;
// New / Import open the entry screens.

import { computed, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { usePermissions } from "@/composables/usePermissions";
import { DOCSTATUS_LABELS } from "@/utils/workforceForms";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();
const { canCreate } = usePermissions();
const { workerOptions } = useFieldEmployeeOptions();

const employeeFilter = ref("");
const statusFilter = ref("");
const filterValues = computed(() => ({
	employee: employeeFilter.value,
	docstatus: statusFilter.value,
}));

const columns = [
	{ key: "name", label: __("ID") },
	{ key: "employee_name", label: __("Worker") },
	{ key: "start_date", label: __("Date") },
	{ key: "total_hours", label: __("Hours"), align: "right" },
	{ key: "total_costing_amount", label: __("Labour cost"), align: "right" },
	{ key: "docstatus", label: __("Status") },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Timesheets") },
];
</script>

<template>
	<DeskPage :title="__('Timesheets')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink
				v-if="canCreate('fieldAttendance')"
				to="/timesheets/import"
				class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
			>
				{{ __("Import") }}
			</RouterLink>
			<RouterLink
				v-if="canCreate('fieldAttendance')"
				to="/timesheets/new"
				class="desk-save-btn !text-xs"
			>
				{{ __("+ New") }}
			</RouterLink>
		</template>

		<DocTypeListView
			doctype="Timesheet"
			:field-order="[
				'name',
				'employee',
				'employee_name',
				'start_date',
				'total_hours',
				'total_costing_amount',
				'docstatus',
			]"
			:columns="columns"
			:search-fields="['name', 'employee_name', 'employee']"
			:base-filters="[['docstatus', '<', 3]]"
			:filter-values="filterValues"
			:filter-field-map="{ employee: 'employee', docstatus: 'docstatus' }"
			cache-key="buildsuite-timesheets"
			row-key="name"
			initial-order-by="start_date desc"
			:search-placeholder="__('Search timesheets…')"
			:empty-message="__('No timesheets yet.')"
			@row-click="(row) => router.push(`/timesheets/${row.name}`)"
		>
			<template #filter-chips>
				<div class="w-56">
					<DeskSearchableSelect
						v-model="employeeFilter"
						:options="workerOptions"
						:placeholder="__('All workers')"
						:search-placeholder="__('Search workers…')"
						allow-clear
					/>
				</div>
				<DeskSelect v-model="statusFilter" class="!w-36">
					<option value="">{{ __("All statuses") }}</option>
					<option value="0">{{ __("Draft") }}</option>
					<option value="1">{{ __("Submitted") }}</option>
					<option value="2">{{ __("Cancelled") }}</option>
				</DeskSelect>
			</template>

			<template #cell-name="{ row }">
				<DeskLink :to="`/timesheets/${row.name}`" class="font-mono text-xs" @click.stop>{{
					row.name
				}}</DeskLink>
			</template>
			<template #cell-employee_name="{ row }">
				<span class="text-ink-900 font-medium">{{
					row.employee_name || row.employee
				}}</span>
			</template>
			<template #cell-start_date="{ row }">
				<span class="text-ink-700">{{ fmtDate(row.start_date) || "—" }}</span>
			</template>
			<template #cell-total_hours="{ row }">
				<span class="tabular-nums text-ink-700">{{ row.total_hours || "—" }}</span>
			</template>
			<template #cell-total_costing_amount="{ row }">
				<span class="tabular-nums text-ink-900 font-medium">{{
					row.total_costing_amount ? fmtINR(row.total_costing_amount) : "—"
				}}</span>
			</template>
			<template #cell-docstatus="{ row }">
				<StatusBadge :status="DOCSTATUS_LABELS[row.docstatus] || 'Draft'" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
