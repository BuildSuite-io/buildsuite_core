<script setup>
// Material Requests — ERPNext Material Request master, in-app list via DocTypeListView.
// Requested-by resolves from the doc owner to a name (not the email). Note: Material
// Request carries no parent `project` (it lives on the line items), so this list has no
// project column/filter — unlike PO / Purchase Receipt. Row / New open the Desk form.
import { computed, ref } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { fmtDate } from "@/utils/format";

const activeCompany = useActiveCompany();
const baseFilters = computed(() =>
	activeCompany.value ? [["company", "=", activeCompany.value]] : []
);

const FIELDS = [
	"name",
	"material_request_type",
	"transaction_date",
	"schedule_date",
	"owner",
	"per_ordered",
	"status",
];
const columns = [
	{ key: "name", label: "MR" },
	{ key: "material_request_type", label: "Type" },
	{ key: "transaction_date", label: "Date" },
	{ key: "schedule_date", label: "Required by" },
	{ key: "owner", label: "Requested by" },
	{ key: "per_ordered", label: "Ordered", align: "right" },
	{ key: "status", label: "Status" },
];

const statusFilter = ref("");
const fromDate = ref("");
const toDate = ref("");
const filterValues = computed(() => ({
	status: statusFilter.value,
	fromDate: fromDate.value,
	toDate: toDate.value,
}));
const filterFieldMap = {
	status: "status",
	fromDate: { field: "transaction_date", op: ">=" },
	toDate: { field: "transaction_date", op: "<=" },
};

function openDesk(row) {
	window.open(`/app/material-request/${encodeURIComponent(row.name)}`, "_blank", "noopener");
}
function openNew() {
	window.open("/app/material-request/new", "_blank", "noopener");
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Material Requests" },
];
</script>

<template>
	<DeskPage title="Material Requests" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button type="button" class="desk-save-btn !text-xs" @click="openNew">
				+ New Request
			</button>
		</template>

		<DocTypeListView
			v-if="activeCompany"
			doctype="Material Request"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name']"
			:base-filters="baseFilters"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			cache-key="buildsuite-material-requests"
			row-key="name"
			initial-order-by="transaction_date desc"
			search-placeholder="Search material request…"
			empty-message="No material requests yet."
			@row-click="openDesk"
		>
			<template #filter-chips>
				<DeskSelect v-model="statusFilter" class="!w-44">
					<option value="">Status: Any</option>
					<option>Draft</option>
					<option>Pending</option>
					<option>Partially Ordered</option>
					<option>Ordered</option>
					<option>Received</option>
					<option>Stopped</option>
					<option>Cancelled</option>
				</DeskSelect>
				<input
					v-model="fromDate"
					type="date"
					title="From (request date)"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
				<input
					v-model="toDate"
					type="date"
					title="To (request date)"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
			</template>

			<template #cell-name="{ row }">
				<span class="font-mono text-[11px] text-ink-600">{{ row.name }}</span>
			</template>
			<template #cell-material_request_type="{ row }">
				<span class="text-ink-700">{{ row.material_request_type || "—" }}</span>
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
			<template #cell-owner="{ row }">
				<div class="flex items-center gap-1.5">
					<UserAvatar :user-id="row.owner" size="xs" show-name />
				</div>
			</template>
			<template #cell-per_ordered="{ row }">
				<span class="tabular-nums text-ink-700"
					>{{ Math.round(row.per_ordered || 0) }}%</span
				>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" size="xs" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
