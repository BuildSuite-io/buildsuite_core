<script setup>
// Purchase Receipts (goods received) — ERPNext Purchase Receipt master, in-app list via
// DocTypeListView. Readable names (supplier_name, project → project_name); row / New open
// the Desk form.
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectNames } from "@/composables/useProjectNames";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { fmtDate, fmtINR } from "@/utils/format";

const router = useRouter();
const { projectName } = useProjectNames();
const activeCompany = useActiveCompany();
const baseFilters = computed(() =>
	activeCompany.value ? [["company", "=", activeCompany.value]] : []
);

const FIELDS = [
	"name",
	"supplier_name",
	"project",
	"posting_date",
	"grand_total",
	"per_billed",
	"status",
];
const columns = [
	{ key: "name", label: "Receipt" },
	{ key: "supplier_name", label: "Supplier" },
	{ key: "project", label: "Project" },
	{ key: "posting_date", label: "Received" },
	{ key: "grand_total", label: "Value", align: "right" },
	{ key: "per_billed", label: "Billed", align: "right" },
	{ key: "status", label: "Status" },
];

const statusFilter = ref("");
const projectFilter = ref("");
const fromDate = ref("");
const toDate = ref("");
const filterValues = computed(() => ({
	status: statusFilter.value,
	project: projectFilter.value,
	fromDate: fromDate.value,
	toDate: toDate.value,
}));
const filterFieldMap = {
	status: "status",
	project: "project",
	fromDate: { field: "posting_date", op: ">=" },
	toDate: { field: "posting_date", op: "<=" },
};

function openDetail(row) {
	router.push(`/procurement/receipts/${row.name}`);
}
function openNew() {
	router.push("/procurement/receipts/new");
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Purchase Receipts" },
];
</script>

<template>
	<DeskPage title="Purchase Receipts" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button type="button" class="desk-save-btn !text-xs" @click="openNew">
				+ New Receipt
			</button>
		</template>

		<DocTypeListView
			v-if="activeCompany"
			doctype="Purchase Receipt"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'supplier_name']"
			:base-filters="baseFilters"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			cache-key="buildsuite-purchase-receipts"
			row-key="name"
			initial-order-by="posting_date desc"
			search-placeholder="Search receipt, supplier…"
			empty-message="No purchase receipts yet."
			@row-click="openDetail"
		>
			<template #filter-chips>
				<DeskSelect v-model="statusFilter" class="!w-44">
					<option value="">Status: Any</option>
					<option>Draft</option>
					<option>To Bill</option>
					<option>Completed</option>
					<option>Return Issued</option>
					<option>Closed</option>
					<option>Cancelled</option>
				</DeskSelect>
				<div class="w-48">
					<DeskLinkPicker
						v-model="projectFilter"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						placeholder="All projects"
					/>
				</div>
				<input
					v-model="fromDate"
					type="date"
					title="From (receipt date)"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
				<input
					v-model="toDate"
					type="date"
					title="To (receipt date)"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
			</template>

			<template #cell-name="{ row }">
				<span class="font-mono text-[11px] text-ink-600">{{ row.name }}</span>
			</template>
			<template #cell-supplier_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.supplier_name || "—" }}</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-ink-700">{{ projectName(row.project) || "—" }}</span>
			</template>
			<template #cell-posting_date="{ row }">
				<span class="text-ink-500 whitespace-nowrap">{{ fmtDate(row.posting_date) }}</span>
			</template>
			<template #cell-grand_total="{ row }">
				<span class="tabular-nums text-ink-900 font-medium">{{
					fmtINR(row.grand_total)
				}}</span>
			</template>
			<template #cell-per_billed="{ row }">
				<span class="tabular-nums text-ink-700"
					>{{ Math.round(row.per_billed || 0) }}%</span
				>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" size="xs" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
