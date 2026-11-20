<script setup>
// Supplier Quotations — ERPNext's Supplier Quotation, in-app list via DocTypeListView
// (pagination / sort / search for free). What suppliers quoted, item by item; compare them
// before placing the order. Row click / New open the in-app detail + form.
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectNames } from "@/composables/useProjectNames";
import { useActiveCompany, activeCompanyFilter } from "@/composables/useActiveCompany";
import { usePermissions } from "@/composables/usePermissions";
import { expireLapsedQuotations } from "@/data/rfqApi";
import { fmtDate, fmtINR } from "@/utils/format";
import { useReportAccess } from "@/composables/useReportAccess";
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
	"quotation_number",
	"custom_request_for_quotation",
	"project",
	"transaction_date",
	"valid_till",
	"total",
	"status",
];
const columns = [
	{ key: "name", label: __("ID") },
	{ key: "supplier_name", label: __("Supplier") },
	{ key: "custom_request_for_quotation", label: __("Request") },
	{ key: "project", label: __("Project") },
	{ key: "transaction_date", label: __("Date") },
	{ key: "valid_till", label: __("Valid till") },
	{ key: "total", label: __("Net value"), align: "right" },
	{ key: "status", label: __("Status") },
];

// ERPNext's daily job stamps Expired on lapsed quotations; run it before the list loads so a
// quotation that ran out this morning already reads (and filters as) Expired.
const ready = ref(false);
onMounted(async () => {
	try {
		await expireLapsedQuotations();
	} catch {
		// the list still loads; a lapsed quotation reads Expired after the nightly job
	}
	ready.value = true;
});

const statusFilter = ref("");
const supplierFilter = ref("");
const filterValues = computed(() => ({
	status: statusFilter.value,
	supplier: supplierFilter.value,
}));
const filterFieldMap = { status: "status", supplier: "supplier" };

const { canOpenReport } = useReportAccess();

function openDetail(row) {
	router.push(`/procurement/supplier-quotations/${row.name}`);
}
function openNew() {
	router.push("/procurement/supplier-quotations/new");
}
function openCompare() {
	router.push("/procurement/supplier-quotation-comparison");
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Supplier Quotation") },
];
</script>

<template>
	<DeskPage
		:title="__('Supplier Quotation')"
		:subtitle="
			__('What suppliers quoted, item by item. Compare them before placing the order.')
		"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="canOpenReport('/procurement/supplier-quotation-comparison')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="openCompare"
			>
				{{ __("Compare quotations") }}
			</button>
			<button
				v-if="canCreate('supplierQuotation')"
				type="button"
				class="desk-save-btn !text-xs"
				data-test="sq-new"
				@click="openNew"
			>
				+ {{ __("New") }}
			</button>
		</template>

		<DocTypeListView
			v-if="activeCompany && ready"
			doctype="Supplier Quotation"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'supplier_name', 'quotation_number']"
			:base-filters="baseFilters"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			cache-key="buildsuite-supplier-quotations"
			row-key="name"
			initial-order-by="transaction_date desc"
			:search-placeholder="__('Search quotation, supplier…')"
			:empty-message="
				__(
					'No supplier quotations yet. Record one from a submitted request for quotation.'
				)
			"
			@row-click="openDetail"
		>
			<template #filter-chips>
				<DeskSelect v-model="statusFilter" class="!w-44">
					<option value="">{{ __("All statuses") }}</option>
					<option value="Draft">{{ __("Draft") }}</option>
					<option value="Submitted">{{ __("Submitted") }}</option>
					<option value="Expired">{{ __("Expired") }}</option>
					<option value="Cancelled">{{ __("Cancelled") }}</option>
				</DeskSelect>
				<div class="w-48">
					<DeskLinkPicker
						v-model="supplierFilter"
						doctype="Supplier"
						label-field="supplier_name"
						value-field="name"
						:placeholder="__('All suppliers')"
					/>
				</div>
			</template>

			<template #cell-name="{ row }">
				<span class="font-mono text-[11px] text-ink-600 whitespace-nowrap">{{
					row.name
				}}</span>
			</template>
			<template #cell-supplier_name="{ row }">
				<span class="block text-ink-900 font-medium">{{ row.supplier_name || "—" }}</span>
				<span v-if="row.quotation_number" class="block text-[11px] text-ink-500">{{
					__("Ref {0}", [row.quotation_number])
				}}</span>
			</template>
			<template #cell-custom_request_for_quotation="{ row }">
				<span class="font-mono text-[11px] text-ink-600">{{
					row.custom_request_for_quotation || "—"
				}}</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-ink-700">{{ projectName(row.project) || "—" }}</span>
			</template>
			<template #cell-transaction_date="{ row }">
				<span class="text-ink-500 whitespace-nowrap">{{
					fmtDate(row.transaction_date)
				}}</span>
			</template>
			<template #cell-valid_till="{ row }">
				<span class="text-ink-500 whitespace-nowrap">{{
					row.valid_till ? fmtDate(row.valid_till) : "—"
				}}</span>
			</template>
			<template #cell-total="{ row }">
				<span class="tabular-nums text-ink-900">{{ fmtINR(row.total) }}</span>
			</template>
			<template #cell-status="{ row }">
				<ProcurementStatusPill :status="row.status" kind="quotation" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
