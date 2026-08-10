<script setup>
// Field Attendance — one sheet per project per day. Submitting a sheet (from
// Desk for now) generates the Labour and Overtime Attendance registers.
//
// The employee count is not shown: child tables don't come back from the list
// API, and Field Attendance has no denormalised count field.

import { computed, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { DOCSTATUS_LABELS } from "@/utils/workforceForms";
import { fmtDate } from "@/utils/format";

const router = useRouter();
const { projectOptions, projectLabel } = useProjectOptions();

const projectFilter = ref("");
const filterValues = computed(() => ({ project: projectFilter.value }));

function onRowClick(row) {
	router.push(`/field-attendance/${row.name}`);
}

const columns = [
	{ key: "name", label: "ID" },
	{ key: "project", label: "Project" },
	{ key: "date", label: "Date" },
	{ key: "status", label: "Day status" },
	{ key: "docstatus", label: "State" },
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
			<RouterLink to="/field-attendance/new" class="desk-save-btn !text-xs">
				+ New
			</RouterLink>
		</template>

		<DocTypeListView
			doctype="Field Attendance"
			:field-order="['name', 'project', 'date', 'status', 'docstatus']"
			:columns="columns"
			:search-fields="['name', 'project']"
			:filter-values="filterValues"
			:filter-field-map="{ project: 'project' }"
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

			<template #cell-status="{ row }">
				<span class="text-ink-700">{{ row.status || "—" }}</span>
			</template>

			<template #cell-docstatus="{ row }">
				<span class="text-ink-600">{{ DOCSTATUS_LABELS[row.docstatus] || "Draft" }}</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
