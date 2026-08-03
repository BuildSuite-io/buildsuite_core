<script setup>
// Subcontractor Work Order list — Desk-styled, mirrors the prototype.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtCompactINR } from "@/utils/format";

const router = useRouter();

const wosRes = useDocTypeList("Subcontractor Work Order", {
	fields: [
		"name",
		"subcontractor_name",
		"project",
		"date",
		"delivery_type",
		"total_value",
		"docstatus",
	],
	orderBy: "date desc",
	pageLength: 0,
	cache: "buildsuite-subcontractor-wo-list",
	// The WO is natively submittable — state is docstatus (Draft/Submitted/Cancelled), not a field.
	transform: (data) =>
		data.map((w) => ({
			id: w.name,
			subcontractor: w.subcontractor_name,
			project: w.project,
			date: w.date,
			delivery_type: w.delivery_type,
			total_value: w.total_value,
			status: { 0: "Draft", 1: "Submitted", 2: "Cancelled" }[w.docstatus] || "Draft",
		})),
});

const search = ref("");
const rows = computed(() => {
	let data = wosRes.data || [];
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(w) =>
				(w.id || "").toLowerCase().includes(q) ||
				(w.subcontractor || "").toLowerCase().includes(q) ||
				(w.project || "").toLowerCase().includes(q)
		);
	return data;
});

const columns = [
	{ key: "id", label: "WO ID" },
	{ key: "subcontractor", label: "Subcontractor" },
	{ key: "project", label: "Project" },
	{ key: "date", label: "Date" },
	{ key: "delivery_type", label: "Type" },
	{ key: "total_value", label: "Value", align: "right" },
	{ key: "status", label: "Status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Work Orders" },
];

function onRowClick(row) {
	router.push(`/subcontractor-work-orders/${row.id}`);
}
</script>

<template>
	<DeskPage title="Work Orders" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/subcontractor-work-orders/new" class="desk-save-btn"
				>+ New</RouterLink
			>
		</template>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="id"
			search-placeholder="Search WO, subcontractor, project…"
			@row-click="onRowClick"
		>
			<template #cell-id="{ row }">
				<DeskLink
					:to="`/subcontractor-work-orders/${row.id}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.id }}</DeskLink
				>
			</template>
			<template #cell-subcontractor="{ row }">
				<span class="text-ink-900 font-medium">{{ row.subcontractor }}</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-xs text-ink-700">{{ row.project }}</span>
			</template>
			<template #cell-date="{ row }">
				<span class="text-xs text-ink-500">{{ fmtDate(row.date) }}</span>
			</template>
			<template #cell-delivery_type="{ row }">
				<span
					v-if="row.delivery_type"
					class="text-[11px] px-1.5 py-0.5 bg-ink-100 text-ink-700 rounded"
					>{{ row.delivery_type }}</span
				>
				<span v-else class="text-ink-300">—</span>
			</template>
			<template #cell-total_value="{ row }">
				<span class="text-xs tabular-nums text-ink-900 font-medium">{{
					fmtCompactINR(row.total_value)
				}}</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ wosRes.loading ? "Loading work orders…" : "No work orders raised yet." }}
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
