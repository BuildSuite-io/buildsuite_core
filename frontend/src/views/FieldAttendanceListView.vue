<script setup>
// Field Attendance — one sheet per project per day. Submitting a sheet (from
// Desk for now) generates the Labour and Overtime Attendance registers.

import { computed, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { usePermissions } from "@/composables/usePermissions";
import { DOCSTATUS_LABELS } from "@/utils/workforceForms";
import { fmtDate } from "@/utils/format";

const router = useRouter();
const { projectOptions, projectLabel } = useProjectOptions();
const { workerOptions } = useFieldEmployeeOptions();
const { canCreate } = usePermissions();

const projectFilter = ref("");
const employeeFilter = ref("");
// String, not number: the filter builder drops falsy values, so 0 (Draft) would never apply.
const statusFilter = ref("");

const filterValues = computed(() => ({
	project: projectFilter.value,
	docstatus: statusFilter.value,
}));

// Child-table filter — filterFieldMap only builds 3-part ones, so it goes via baseFilters.
const baseFilters = computed(() =>
	employeeFilter.value
		? [["Field Attendance Employee", "employee", "=", employeeFilter.value]]
		: [],
);

function onRowClick(row) {
	router.push(`/field-attendance/${row.name}`);
}

const columns = [
	{ key: "name", label: "ID" },
	{ key: "project", label: "Project" },
	{ key: "date", label: "Date" },
	{ key: "employees_count", label: "Employees", align: "right" },
	{ key: "docstatus", label: "Status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Field Attendance" },
];
</script>

<template>
	<DeskPage title="Field Attendance" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink
				v-if="canCreate('fieldAttendance')"
				to="/field-attendance/new"
				class="desk-save-btn !text-xs"
			>
				+ New
			</RouterLink>
		</template>

		<DocTypeListView
			doctype="Field Attendance"
			:field-order="['name', 'project', 'date', 'employees_count', 'docstatus']"
			:columns="columns"
			:search-fields="['name', 'project']"
			:base-filters="baseFilters"
			:filter-values="filterValues"
			:filter-field-map="{ project: 'project', docstatus: 'docstatus' }"
			cache-key="buildsuite-field-attendance"
			row-key="name"
			initial-order-by="date desc"
			search-placeholder="Search attendance…"
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<div class="w-56">
					<DeskSearchableSelect
						v-model="projectFilter"
						:options="projectOptions"
						placeholder="All projects"
						search-placeholder="Search projects…"
						allow-clear
					/>
				</div>

				<div class="w-56">
					<DeskSearchableSelect
						v-model="employeeFilter"
						:options="workerOptions"
						placeholder="All employees"
						search-placeholder="Search employees…"
						allow-clear
					/>
				</div>

				<DeskSelect v-model="statusFilter" class="!w-36">
					<option value="">All statuses</option>
					<option value="0">Draft</option>
					<option value="1">Submitted</option>
					<option value="2">Cancelled</option>
				</DeskSelect>
			</template>

			<template #cell-name="{ row }">
				<DeskLink
					:to="`/field-attendance/${row.name}`"
					@click.stop
					class="font-mono text-xs"
				>
					{{ row.name }}
				</DeskLink>
			</template>

			<template #cell-project="{ row }">
				<span class="text-ink-700">{{ projectLabel(row.project) || "—" }}</span>
			</template>

			<template #cell-date="{ row }">
				<span class="text-ink-700">{{ fmtDate(row.date) || "—" }}</span>
			</template>

			<template #cell-employees_count="{ row }">
				<span class="tabular-nums text-ink-700">{{ row.employees_count || 0 }}</span>
			</template>

			<template #cell-docstatus="{ row }">
				<StatusBadge :status="DOCSTATUS_LABELS[row.docstatus] || 'Draft'" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
