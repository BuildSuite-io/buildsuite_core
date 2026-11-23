<script setup>
// Purchase Receipts (goods received) — ERPNext Purchase Receipt master, in-app list via
// DocTypeListView. Readable names (supplier_name, project → project_name), the prototype's
// status pills + billed bar; row / New open the in-app detail + form.
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectNames } from "@/composables/useProjectNames";
import { getReceiptPurchaseOrders } from "@/data/procurementApi";
import { useActiveCompany, activeCompanyFilter } from "@/composables/useActiveCompany";
import { fmtDate, fmtCompactINR } from "@/utils/format";
import { usePermissions } from "@/composables/usePermissions";
import { __ } from "@/utils/translate";

const router = useRouter();
const { canCreate } = usePermissions();
const { projectName } = useProjectNames();
const activeCompany = useActiveCompany();
// Toggle-gated: [] when company awareness is off, so the list shows every company.
const baseFilters = activeCompanyFilter();

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
	{ key: "name", label: __("Receipt") },
	// Not a field: the receipt's order(s), read off its lines for the rows on screen.
	{ key: "purchase_order", label: __("PO") },
	{ key: "supplier_name", label: __("Supplier") },
	{ key: "project", label: __("Project") },
	{ key: "posting_date", label: __("Received") },
	{ key: "grand_total", label: __("Value"), align: "right" },
	{ key: "per_billed", label: __("Billed"), align: "right" },
	{ key: "status", label: __("Status") },
];

// The PO(s) each receipt on screen was received against — fetched per page (paging, filters,
// search) for rows not seen yet.
const receiptPOs = ref({});
async function onRowsChange(rows) {
	const names = (rows || []).map((r) => r.name).filter((n) => n && !(n in receiptPOs.value));
	if (!names.length) return;
	try {
		receiptPOs.value = {
			...receiptPOs.value,
			...((await getReceiptPurchaseOrders(names)) || {}),
		};
	} catch {
		// the list still shows; only the PO column stays blank for these rows
	}
}

const statusFilter = ref("");
const projectFilter = ref("");
const supplierFilter = ref("");
const fromDate = ref("");
const toDate = ref("");
const filterValues = computed(() => ({
	status: statusFilter.value,
	project: projectFilter.value,
	supplier: supplierFilter.value,
	fromDate: fromDate.value,
	toDate: toDate.value,
}));
const filterFieldMap = {
	status: "status",
	project: "project",
	supplier: "supplier",
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
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Purchase Receipts") },
];
</script>

<template>
	<DeskPage :title="__('Purchase Receipts')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button
				v-if="canCreate('purchaseReceipt')"
				type="button"
				class="desk-save-btn !text-xs"
				@click="openNew"
			>
				+ {{ __("New Receipt") }}
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
			:search-placeholder="__('Search receipt, supplier…')"
			:empty-message="__('No purchase receipts yet.')"
			@row-click="openDetail"
			@rows-change="onRowsChange"
		>
			<template #filter-chips>
				<DeskSelect v-model="statusFilter" class="!w-44">
					<option value="">{{ __("Status: Any") }}</option>
					<option value="Draft">{{ __("Draft") }}</option>
					<option value="To Bill">{{ __("To Bill") }}</option>
					<option value="Completed">{{ __("Completed") }}</option>
					<option value="Return Issued">{{ __("Return Issued") }}</option>
					<option value="Closed">{{ __("Closed") }}</option>
					<option value="Cancelled">{{ __("Cancelled") }}</option>
				</DeskSelect>
				<div class="w-48">
					<DeskLinkPicker
						v-model="projectFilter"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:placeholder="__('All projects')"
					/>
				</div>
				<div class="w-48">
					<DeskLinkPicker
						v-model="supplierFilter"
						doctype="Supplier"
						label-field="supplier_name"
						value-field="name"
						:search-fields="['supplier_name', 'name']"
						allow-clear
						:placeholder="__('All suppliers')"
					/>
				</div>
				<input
					v-model="fromDate"
					type="date"
					:title="__('From (receipt date)')"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
				<input
					v-model="toDate"
					type="date"
					:title="__('To (receipt date)')"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
			</template>

			<template #cell-name="{ row }">
				<span class="font-mono text-[11px] text-ink-600">{{ row.name }}</span>
			</template>
			<template #cell-purchase_order="{ row }">
				<template v-if="row.name in receiptPOs">
					<span
						v-if="receiptPOs[row.name].length"
						class="font-mono text-xs text-ink-600 whitespace-nowrap"
						>{{ receiptPOs[row.name].join(", ") }}</span
					>
					<span
						v-else
						class="text-[11px] px-2 py-0.5 rounded-full bg-danger-50 text-danger-700 whitespace-nowrap"
						>{{ __("No PO — resolve") }}</span
					>
				</template>
				<span v-else class="text-ink-400">—</span>
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
				<span class="tabular-nums text-ink-700">{{ fmtCompactINR(row.grand_total) }}</span>
			</template>
			<template #cell-per_billed="{ row }">
				<span class="flex items-center gap-1.5 justify-end">
					<span class="w-14 h-1.5 rounded-full bg-ink-100 overflow-hidden">
						<span
							class="block h-full rounded-full"
							:class="
								(row.per_billed || 0) >= 100 ? 'bg-success-500' : 'bg-info-500'
							"
							:style="{ width: Math.min(100, row.per_billed || 0) + '%' }"
						></span>
					</span>
					<span class="text-[11px] tabular-nums text-ink-500"
						>{{ Math.round(row.per_billed || 0) }}%</span
					>
				</span>
			</template>
			<template #cell-status="{ row }">
				<ProcurementStatusPill :status="row.status" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
