<script setup>
// Purchase Orders — ERPNext Purchase Order master, in-app list via DocTypeListView
// (pagination / sort / search for free). Columns show readable names (supplier_name,
// project → project_name) rather than record ids. Row click / New open the Desk form.
import { computed, ref } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectNames } from "@/composables/useProjectNames";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { fmtDate, fmtINR } from "@/utils/format";

const { projectName } = useProjectNames();
const activeCompany = useActiveCompany();
const baseFilters = computed(() =>
	activeCompany.value ? [["company", "=", activeCompany.value]] : []
);

const FIELDS = [
	"name",
	"supplier_name",
	"project",
	"transaction_date",
	"schedule_date",
	"grand_total",
	"per_received",
	"status",
];
const columns = [
	{ key: "name", label: "PO" },
	{ key: "supplier_name", label: "Supplier" },
	{ key: "project", label: "Project" },
	{ key: "transaction_date", label: "Ordered" },
	{ key: "schedule_date", label: "Required by" },
	{ key: "grand_total", label: "Value", align: "right" },
	{ key: "per_received", label: "Received", align: "right" },
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
	fromDate: { field: "transaction_date", op: ">=" },
	toDate: { field: "transaction_date", op: "<=" },
};

function openDesk(row) {
	window.open(`/app/purchase-order/${encodeURIComponent(row.name)}`, "_blank", "noopener");
}
function openNew() {
	window.open("/app/purchase-order/new", "_blank", "noopener");
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Purchase Orders" },
];
</script>

<template>
	<DeskPage title="Purchase Orders" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button type="button" class="desk-save-btn !text-xs" @click="openNew">+ New PO</button>
		</template>

		<DocTypeListView
			v-if="activeCompany"
			doctype="Purchase Order"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'supplier_name']"
			:base-filters="baseFilters"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			cache-key="buildsuite-purchase-orders"
			row-key="name"
			initial-order-by="transaction_date desc"
			search-placeholder="Search PO, supplier…"
			empty-message="No purchase orders yet."
			@row-click="openDesk"
		>
			<template #filter-chips>
				<DeskSelect v-model="statusFilter" class="!w-44">
					<option value="">Status: Any</option>
					<option>Draft</option>
					<option>To Receive and Bill</option>
					<option>To Bill</option>
					<option>To Receive</option>
					<option>Completed</option>
					<option>On Hold</option>
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
					title="From (order date)"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
				<input
					v-model="toDate"
					type="date"
					title="To (order date)"
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
			<template #cell-transaction_date="{ row }">
				<span class="text-ink-500 whitespace-nowrap">{{
					fmtDate(row.transaction_date)
				}}</span>
			</template>
			<template #cell-schedule_date="{ row }">
				<span class="text-ink-500 whitespace-nowrap">{{
					row.schedule_date ? fmtDate(row.schedule_date) : "—"
				}}</span>
			</template>
			<template #cell-grand_total="{ row }">
				<span class="tabular-nums text-ink-900 font-medium">{{
					fmtINR(row.grand_total)
				}}</span>
			</template>
			<template #cell-per_received="{ row }">
				<span class="tabular-nums text-ink-700"
					>{{ Math.round(row.per_received || 0) }}%</span
				>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" size="xs" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
