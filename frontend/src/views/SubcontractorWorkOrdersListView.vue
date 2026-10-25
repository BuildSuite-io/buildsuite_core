<script setup>
// Subcontractor Work Order list — Desk-styled, mirrors the prototype.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import { usePermissions } from "@/composables/usePermissions";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { fmtDate, fmtCompactINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();
const { projectName } = useProjectNames();
const { canCreate, canRead } = usePermissions();
const { projectOptions } = useProjectOptions();

// Register filters: subcontractor, project, state, order period.
const subFilter = ref("");
const projectFilter = ref("");
// String, not number: the filter builder drops falsy values, so 0 (Draft) would never apply.
const statusFilter = ref("");
const fromDate = ref("");
const toDate = ref("");
const filterValues = computed(() => ({
	subcontractor: subFilter.value,
	project: projectFilter.value,
	docstatus: statusFilter.value,
	from: fromDate.value,
	to: toDate.value,
}));
const filterFieldMap = {
	subcontractor: "subcontractor",
	project: "project",
	docstatus: "docstatus",
	from: { field: "date", op: ">=" },
	to: { field: "date", op: "<=" },
};
const subRes = useDocTypeList("Subcontractor Work Order", {
	fields: ["subcontractor", "subcontractor_name"],
	pageLength: 0,
	cache: "buildsuite-wo-subcontractor-options",
});
const subOptions = computed(() => {
	const seen = new Map();
	for (const w of subRes.data || []) {
		if (w.subcontractor) seen.set(w.subcontractor, w.subcontractor_name || w.subcontractor);
	}
	return [...seen]
		.map(([value, label]) => ({ value, label }))
		.sort((a, b) => a.label.localeCompare(b.label));
});

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
	{ key: "name", label: __("WO ID") },
	{ key: "subcontractor_name", label: __("Subcontractor") },
	{ key: "project", label: __("Project") },
	{ key: "date", label: __("Date") },
	{ key: "delivery_type", label: __("Type") },
	{ key: "total_value", label: __("Value"), align: "right" },
	// "% Billed" is hidden for personas that can't read Subcontractor Bills (no bill fetch).
	...(canReadBills.value
		? [{ key: "percent", label: __("% Billed"), align: "right", fields: ["total_value"] }]
		: []),
	{ key: "status", label: __("Status"), fields: ["docstatus"] },
]);

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Subcontract"), to: "/subcontract" },
	{ label: __("Work Orders") },
];

function onRowClick(row) {
	router.push(`/subcontractor-work-orders/${encodeURIComponent(row.name)}`);
}
</script>

<template>
	<DeskPage :title="__('Work Orders')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink
				v-if="canCreate('subcontractorWorkOrder')"
				to="/subcontractor-work-orders/new"
				class="desk-save-btn"
				>{{ __("+ New") }}</RouterLink
			>
		</template>

		<DocTypeListView
			doctype="Subcontractor Work Order"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'subcontractor_name', 'project']"
			cache-key="buildsuite-subcontractor-wo-list"
			row-key="name"
			:search-placeholder="__('Search WO, subcontractor, project…')"
			:empty-message="__('No work orders raised yet.')"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<div class="w-56">
					<DeskSearchableSelect
						v-model="subFilter"
						:options="subOptions"
						:placeholder="__('All subcontractors')"
						:search-placeholder="__('Search subcontractors…')"
						allow-clear
					/>
				</div>
				<div class="w-56">
					<DeskSearchableSelect
						v-model="projectFilter"
						:options="projectOptions"
						:placeholder="__('All projects')"
						:search-placeholder="__('Search projects…')"
						allow-clear
					/>
				</div>
				<DeskSelect v-model="statusFilter" class="!w-36">
					<option value="">{{ __("Any status") }}</option>
					<option value="0">{{ __("Draft") }}</option>
					<option value="1">{{ __("Submitted") }}</option>
					<option value="2">{{ __("Cancelled") }}</option>
				</DeskSelect>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Dated")
					}}</span>
					<DeskInput v-model="fromDate" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">{{ __("to") }}</span>
					<DeskInput v-model="toDate" type="date" class="!w-36" />
				</label>
			</template>

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
					>{{ __(row.delivery_type) }}</span
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
