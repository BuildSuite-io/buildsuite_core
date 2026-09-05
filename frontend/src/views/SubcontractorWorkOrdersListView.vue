<script setup>
// Subcontractor Work Order list — Desk-styled, mirrors the prototype.

import { computed } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import { usePermissions } from "@/composables/usePermissions";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { fmtDate, fmtCompactINR } from "@/utils/format";

const router = useRouter();
const { projectName } = useProjectNames();
const { canCreate, canRead } = usePermissions();

// The "% Billed" column is sourced from Subcontractor Bills. A persona without Bill read
// (e.g. Estimator) neither fetches them (which would 403) nor sees the column.
const canReadBills = computed(() => canRead("subcontractorBill"));

// Billed-to-date per work order (sum of non-cancelled Subcontractor Bill gross) → % billed.
// Kept as a lightweight full fetch feeding the derived "% Billed" cell.
const billsRes = useDocTypeList("Subcontractor Bill", {
	fields: ["name", "work_order", "gross", "docstatus"],
	orderBy: "modified desc",
	pageLength: 0,
	cache: "buildsuite-subcontractor-bills-all",
	auto: canReadBills.value, // skip the fetch (and its 403) when the persona can't read bills
});
const billedByWO = computed(() => {
	const map = {};
	for (const b of billsRes.data || []) {
		if (b.docstatus === 2 || !b.work_order) continue; // skip cancelled
		map[b.work_order] = (map[b.work_order] || 0) + (Number(b.gross) || 0);
	}
	return map;
});
function woPercentBilled(row) {
	const total = Number(row.total_value) || 0;
	if (total <= 0) return 0;
	return Math.min(100, Math.round(((billedByWO.value[row.name] || 0) / total) * 1000) / 10);
}

function woStatus(row) {
	return { 0: "Draft", 1: "Submitted", 2: "Cancelled" }[row.docstatus] || "Draft";
}

const FIELDS = [
	"name",
	"subcontractor_name",
	"project",
	"date",
	"delivery_type",
	"total_value",
	"docstatus",
];

// DocTypeListView fetches each column's `fields` (falling back to its `key`), so DERIVED
// columns must name the real fields they read — otherwise their key is queried as a field:
// "percent" 417s (no such field) and "status" (a stale, unqueryable legacy column) would too,
// while `docstatus` — which drives the real status — never gets fetched, so every row reads
// as Draft. `percent` is computed from total_value + the bills fetch; `status` from docstatus.
const columns = computed(() => [
	{ key: "name", label: "WO ID" },
	{ key: "subcontractor_name", label: "Subcontractor" },
	{ key: "project", label: "Project" },
	{ key: "date", label: "Date" },
	{ key: "delivery_type", label: "Type" },
	{ key: "total_value", label: "Value", align: "right" },
	// "% Billed" is hidden for personas that can't read Subcontractor Bills (no bill fetch).
	...(canReadBills.value
		? [{ key: "percent", label: "% Billed", align: "right", fields: ["total_value"] }]
		: []),
	{ key: "status", label: "Status", fields: ["docstatus"] },
]);

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Work Orders" },
];

function onRowClick(row) {
	router.push(`/subcontractor-work-orders/${encodeURIComponent(row.name)}`);
}
</script>

<template>
	<DeskPage title="Work Orders" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink
				v-if="canCreate('subcontractorWorkOrder')"
				to="/subcontractor-work-orders/new"
				class="desk-save-btn"
				>+ New</RouterLink
			>
		</template>

		<DocTypeListView
			doctype="Subcontractor Work Order"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'subcontractor_name', 'project']"
			cache-key="buildsuite-subcontractor-wo-list"
			row-key="name"
			search-placeholder="Search WO, subcontractor, project…"
			empty-message="No work orders raised yet."
			@row-click="onRowClick"
		>
			<template #cell-name="{ row }">
				<DeskLink
					:to="`/subcontractor-work-orders/${encodeURIComponent(row.name)}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.name }}</DeskLink
				>
			</template>
			<template #cell-subcontractor_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.subcontractor_name }}</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-xs text-ink-700">{{ projectName(row.project) }}</span>
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
			<template #cell-percent="{ row }">
				<span class="text-xs tabular-nums text-ink-700">{{ woPercentBilled(row) }}%</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="woStatus(row)" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
