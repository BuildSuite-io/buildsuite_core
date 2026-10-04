<script setup>
// Measurement Book list — Desk-styled, mirrors the prototype. Sits at
// project level; each MB carries a work_order link so you can see which
// WO it feeds.

import { ref, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { getMeasurementBookEntryCounts } from "@/data/subcontractApi";
import { useProjectNames } from "@/composables/useProjectNames";
import { usePermissions } from "@/composables/usePermissions";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();
const { projectName } = useProjectNames();
const { canCreate } = usePermissions();

// Entry count per MB (child rows aren't listable client-side by non-admins).
const entryCounts = ref({});
onMounted(async () => {
	try {
		entryCounts.value = (await getMeasurementBookEntryCounts()) || {};
	} catch {
		entryCounts.value = {};
	}
});

const FIELDS = ["name", "project", "work_order", "date", "measured_total", "status"];

const columns = [
	{ key: "name", label: __("MB ID") },
	{ key: "project", label: __("Project") },
	{ key: "work_order", label: __("Work Order") },
	{ key: "date", label: __("Date") },
	{ key: "entries", label: __("Entries"), align: "right" },
	{ key: "measured_total", label: __("Measured"), align: "right" },
	{ key: "status", label: __("Status") },
];

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Subcontract"), to: "/subcontract" },
	{ label: __("Measurement Books") },
];

function onRowClick(row) {
	router.push(`/measurement-books/${row.name}`);
}
</script>

<template>
	<DeskPage :title="__('Measurement Books')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink
				v-if="canCreate('measurementBook')"
				to="/measurement-books/new"
				class="desk-save-btn"
				>{{ __("+ New") }}</RouterLink
			>
		</template>

		<DocTypeListView
			doctype="Measurement Book"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'work_order', 'project']"
			cache-key="buildsuite-measurement-book-list"
			row-key="name"
			:search-placeholder="__('Search MB, WO, project…')"
			:empty-message="__('No measurement books recorded yet.')"
			@row-click="onRowClick"
		>
			<template #cell-name="{ row }">
				<DeskLink
					:to="`/measurement-books/${row.name}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.name }}</DeskLink
				>
			</template>
			<template #cell-project="{ row }">
				<span class="text-xs text-ink-700">{{ projectName(row.project) }}</span>
			</template>
			<template #cell-work_order="{ row }">
				<DeskLink
					:to="`/subcontractor-work-orders/${encodeURIComponent(row.work_order)}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.work_order }}</DeskLink
				>
			</template>
			<template #cell-date="{ row }">
				<span class="text-xs text-ink-500">{{ fmtDate(row.date) }}</span>
			</template>
			<template #cell-entries="{ row }">
				<span class="text-xs tabular-nums text-ink-700">{{
					entryCounts[row.name] || 0
				}}</span>
			</template>
			<template #cell-measured_total="{ row }">
				<span class="text-xs tabular-nums text-info-700 font-medium">{{
					Number(row.measured_total || 0).toLocaleString("en-IN")
				}}</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
