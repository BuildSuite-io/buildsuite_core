<script setup>
// Overtime Attendance Register — read-only. Rows are generated when a Field
// Attendance sheet carrying overtime hours is submitted.

import { computed, ref } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { fmtDate, fmtINR } from "@/utils/format";

const { projectOptions, projectLabel } = useProjectOptions();

const projectFilter = ref("");
const filterValues = computed(() => ({ project: projectFilter.value }));

const columns = [
	{ key: "overtime_date", label: "Date" },
	{ key: "employee_name", label: "Worker" },
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
	<DeskPage title="Overtime Attendance Register" :breadcrumbs="breadcrumbs">
		<DocTypeListView
			doctype="Overtime Attendance Register"
			:field-order="[
				'overtime_date',
				'employee_name',
				'project',
				'overtime_hours',
				'overtime_rate',
				'overtime_wage_calculated',
			]"
			:columns="columns"
			:search-fields="['employee_name', 'name', 'project']"
			:filter-values="filterValues"
			:filter-field-map="{ project: 'project' }"
			:base-filters="[['docstatus', '<', 2]]"
			cache-key="buildsuite-overtime-attendance"
			row-key="name"
			initial-order-by="overtime_date desc"
			search-placeholder="Search worker / project…"
			empty-message="No overtime yet — submit a Field Attendance with overtime hours."
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
			</template>

			<template #cell-overtime_date="{ row }">
				<span class="text-ink-700">{{ fmtDate(row.overtime_date) || "—" }}</span>
			</template>

			<template #cell-employee_name="{ row }">
				<span class="text-ink-900 font-medium">{{
					row.employee_name || row.employee
				}}</span>
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
