<script setup>
// Procurement › Supplier Bills — the bills suppliers send for goods and services: ERPNext Purchase
// Invoices that are NOT a subcontractor bill's generated invoice (those belong to Subcontract ›
// Subcontractor Bills; Project Finance › Bills shows both). Columns, state filter and wording follow
// the prototype's Supplier Bill list. A row / New open the supplier bill screens (paying a bill stays
// in Project Finance › Bills).
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectNames } from "@/composables/useProjectNames";
import { getSupplierBillPurchaseOrders } from "@/data/supplierBillApi";
import { useActiveCompany, activeCompanyFilter } from "@/composables/useActiveCompany";
import { usePermissions } from "@/composables/usePermissions";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const route = useRoute();
const router = useRouter();
const { canCreate } = usePermissions();
const { projectName } = useProjectNames();
const activeCompany = useActiveCompany();
// Toggle-gated: [] when company awareness is off, so the list shows every company.
const companyFilter = activeCompanyFilter();

// Draft / Submitted / Cancelled is the document's state (docstatus 0 / 1 / 2). Applied as a base
// filter: the list's value filters skip a 0, which Draft is. ?state= deep-links set it.
const STATES = { Draft: 0, Submitted: 1, Cancelled: 2 };
const stateFilter = ref(route.query.state in STATES ? route.query.state : "");
const baseFilters = computed(() => [
	...companyFilter.value,
	// A subcontractor bill's own generated invoice carries `subcontractor_bill`: not a supplier bill.
	["subcontractor_bill", "is", "not set"],
	...(stateFilter.value ? [["docstatus", "=", STATES[stateFilter.value]]] : []),
]);

const FIELDS = [
	"name",
	"bill_no",
	"supplier_name",
	"project",
	"posting_date",
	"total",
	"grand_total",
	"docstatus",
	"status",
];
const columns = [
	{ key: "name", label: __("Bill ID"), fields: ["name", "bill_no"] },
	{ key: "supplier_name", label: __("Supplier") },
	// Not a field: the bill's order(s), read off its lines for the rows on screen.
	{ key: "purchase_order", label: __("PO") },
	{ key: "project", label: __("Project") },
	{ key: "posting_date", label: __("Date") },
	{ key: "total", label: __("Gross"), align: "right" },
	{ key: "grand_total", label: __("Net payable"), align: "right" },
	{ key: "status", label: __("Status"), fields: ["status", "docstatus"] },
];

// The PO(s) each bill on screen was raised against — fetched per page for rows not seen yet.
const billPOs = ref({});
async function onRowsChange(rows) {
	const names = (rows || []).map((r) => r.name).filter((n) => n && !(n in billPOs.value));
	if (!names.length) return;
	try {
		billPOs.value = {
			...billPOs.value,
			...((await getSupplierBillPurchaseOrders(names)) || {}),
		};
	} catch {
		// the list still shows; only the PO column stays blank for these rows
	}
}

const stateOf = (row) =>
	Number(row.docstatus) === 1
		? "Submitted"
		: Number(row.docstatus) === 2
		? "Cancelled"
		: "Draft";

function openDetail(row) {
	router.push(`/project-finance/supplier-bills/${row.name}`);
}
function openNew() {
	router.push("/project-finance/supplier-bills/new");
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Supplier Bill") },
];
</script>

<template>
	<DeskPage :title="__('Supplier Bill')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button
				v-if="canCreate('supplierBill')"
				type="button"
				class="desk-save-btn !text-xs"
				@click="openNew"
			>
				+ {{ __("New Supplier Bill") }}
			</button>
		</template>

		<DocTypeListView
			v-if="activeCompany"
			doctype="Purchase Invoice"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'supplier_name', 'bill_no']"
			:base-filters="baseFilters"
			cache-key="buildsuite-procurement-supplier-bills"
			row-key="name"
			initial-order-by="posting_date desc"
			:search-placeholder="__('Search bill, supplier, invoice no…')"
			:empty-message="__('No supplier bills yet.')"
			@row-click="openDetail"
			@rows-change="onRowsChange"
		>
			<template #filter-chips>
				<DeskSelect v-model="stateFilter" class="!w-40">
					<option value="">{{ __("All states") }}</option>
					<option v-for="s in Object.keys(STATES)" :key="s" :value="s">
						{{ __(s) }}
					</option>
				</DeskSelect>
			</template>

			<template #cell-name="{ row }">
				<span class="font-mono text-[11px] text-ink-600 whitespace-nowrap">{{
					row.name
				}}</span>
				<div
					v-if="row.bill_no && row.bill_no !== row.name"
					class="text-[10px] text-ink-400 font-mono"
				>
					{{ row.bill_no }}
				</div>
			</template>
			<template #cell-supplier_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.supplier_name || "—" }}</span>
			</template>
			<template #cell-purchase_order="{ row }">
				<template v-if="row.name in billPOs">
					<span
						v-if="billPOs[row.name].length"
						class="font-mono text-xs text-ink-600 whitespace-nowrap"
						>{{ billPOs[row.name].join(", ") }}</span
					>
					<span v-else class="text-xs text-ink-400 italic">{{ __("Direct") }}</span>
				</template>
				<span v-else class="text-ink-400">—</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-xs text-ink-600">{{ projectName(row.project) || "—" }}</span>
			</template>
			<template #cell-posting_date="{ row }">
				<span class="text-xs text-ink-500 whitespace-nowrap">{{
					fmtDate(row.posting_date)
				}}</span>
			</template>
			<template #cell-total="{ row }">
				<span class="text-xs tabular-nums text-ink-900 font-medium">{{
					fmtINR(row.total)
				}}</span>
			</template>
			<template #cell-grand_total="{ row }">
				<span class="text-xs tabular-nums text-ink-900">{{
					fmtINR(row.grand_total)
				}}</span>
			</template>
			<template #cell-status="{ row }">
				<div class="flex items-center gap-1.5">
					<StatusBadge :status="stateOf(row)" size="xs" />
					<StatusBadge
						v-if="Number(row.docstatus) === 1 && row.status"
						:status="row.status"
						size="xs"
					/>
				</div>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
