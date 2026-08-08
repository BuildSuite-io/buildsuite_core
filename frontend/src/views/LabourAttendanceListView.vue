<script setup>
// Labour Attendance Register — read-only. Rows are generated when a Field
// Attendance sheet is submitted, never created by hand here.

import { computed, ref } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { fmtDate, fmtINR } from "@/utils/format";

const { projectOptions, projectLabel } = useProjectOptions();

const projectFilter = ref("");
const filterValues = computed(() => ({ project: projectFilter.value }));

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
	<DeskPage title="Labour Attendance Register" :breadcrumbs="breadcrumbs">
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
			:filter-field-map="{ project: 'project' }"
			:base-filters="[['docstatus', '<', 2]]"
			cache-key="buildsuite-labour-attendance"
			row-key="name"
			initial-order-by="attendance_date desc"
			search-placeholder="Search worker / project…"
			empty-message="No labour attendance yet — submit a Field Attendance."
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

			<template #cell-attendance_date="{ row }">
				<span class="text-ink-700">{{ fmtDate(row.attendance_date) || "—" }}</span>
			</template>

			<template #cell-employee_name="{ row }">
				<span class="text-ink-900 font-medium">{{
					row.employee_name || row.employee
				}}</span>
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
