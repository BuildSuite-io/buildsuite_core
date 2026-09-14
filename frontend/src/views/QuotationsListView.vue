<script setup>
// ERPNext's Quotation. The cards cover every quotation; the table below is filtered.

import { ref, computed, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useCustomerOptions } from "@/composables/useCustomerOptions";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtCurrency, fmtCompactCurrency, fmtDate } from "@/utils/format";
import { getQuotationSummary } from "@/data/quotationApi";
import { awaitsAnswer, statusLabel } from "@/data/quotationStatus";

const router = useRouter();
const { customerOptions } = useCustomerOptions();

function openQuotation(row) {
	router.push(`/quotations/${encodeURIComponent(row.name)}`);
}

const customerFilter = ref("");
const customerTypeFilter = ref("");
const statusFilter = ref("");
const fromFilter = ref("");
const toFilter = ref("");

const filterValues = computed(() => ({
	customer: customerFilter.value,
	customer_type: customerTypeFilter.value,
	status: statusFilter.value,
	from: fromFilter.value,
	to: toFilter.value,
}));

const summary = ref({ pipeline_value: null, won_value: null, win_rate: null, lapsed_count: null });

onMounted(async () => {
	try {
		summary.value = await getQuotationSummary();
	} catch {
		// Cards stay "—". The list below does not depend on this.
	}
});

const TODAY = new Date().toISOString().slice(0, 10);

const isLapsed = (row) => awaitsAnswer(row.status) && row.valid_till < TODAY;

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Estimation", to: "/estimation" },
	{ label: "Quotations" },
];

const FIELDS = [
	"name",
	"title",
	"party_name",
	"customer_type",
	"transaction_date",
	"valid_till",
	"grand_total",
	"currency",
	"status",
];

const columns = [
	{ key: "name", label: "Quotation" },
	{ key: "title", label: "For" },
	{ key: "party_name", label: "Customer" },
	{ key: "transaction_date", label: "Issued" },
	{ key: "valid_till", label: "Valid to" },
	{ key: "grand_total", label: "Value", align: "right" },
	{ key: "status", label: "Status" },
];
</script>

<template>
	<DeskPage title="Quotations"
		subtitle="Priced offers to customers who asked you for a price. Nothing here touches an estimate — a price you offer is not work you have committed to."
		:breadcrumbs="breadcrumbs" printable>
		<template #actions>
			<RouterLink to="/quotations/new" class="desk-save-btn !text-xs">+ New</RouterLink>
		</template>

		<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Out with customers
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums">
					{{
						summary.pipeline_value === null
							? "—"
							: fmtCompactCurrency(summary.pipeline_value)
					}}
				</div>
				<div class="text-[10px] text-ink-500">sent, no answer yet</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Won
				</div>
				<div class="text-base font-semibold text-success-700 tabular-nums">
					{{ summary.won_value === null ? "—" : fmtCompactCurrency(summary.won_value) }}
				</div>
				<div class="text-[10px] text-ink-500">accepted by the customer</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Win rate
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums">
					{{ summary.win_rate === null ? "—" : summary.win_rate + "%" }}
				</div>
				<div class="text-[10px] text-ink-500">
					{{
						summary.win_rate === null
							? "nothing decided yet"
							: "of quotations actually decided"
					}}
				</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Past their validity
				</div>
				<div class="text-base font-semibold tabular-nums"
					:class="summary.lapsed_count ? 'text-warning-700' : 'text-ink-900'">
					{{ summary.lapsed_count ?? "—" }}
				</div>
				<div class="text-[10px] text-ink-500">chase, or let them go</div>
			</div>
		</div>

		<DocTypeListView doctype="Quotation" :field-order="FIELDS" :columns="columns" :filter-values="filterValues"
			:filter-field-map="{
				customer: 'party_name',
				customer_type: 'customer_type',
				status: 'status',
				from: { field: 'transaction_date', op: '>=' },
				to: { field: 'transaction_date', op: '<=' },
			}" :search-fields="['name', 'party_name', 'title']" cache-key="buildsuite-quotation-list" row-key="name"
			search-placeholder="Search quotation / customer / scope…" empty-message="No quotations yet. Build one when a customer asks you for a price."
			@row-click="openQuotation">
			<template #filter-chips>
				<DeskSearchableSelect v-model="customerFilter" :options="customerOptions" allow-clear
					placeholder="Customer: Any" search-placeholder="Search customers…" class="!w-52" />

				<DeskSelect v-model="customerTypeFilter" class="!w-44">
					<option value="">Customer type: Any</option>
					<option>Homebuyer</option>
					<option>Private Client</option>
					<option>Main Contractor</option>
				</DeskSelect>

				<DeskSelect v-model="statusFilter" class="!w-40">
					<option value="">Status: Any</option>
					<option value="Draft">Draft</option>
					<option value="Open">Sent</option>
					<option value="Replied">Replied</option>
					<option value="Partially Ordered">Partially accepted</option>
					<option value="Ordered">Accepted</option>
					<option value="Lost">Rejected</option>
					<option value="Expired">Expired</option>
					<option value="Cancelled">Cancelled</option>
				</DeskSelect>

				<DeskInput v-model="fromFilter" type="date" class="!w-36" />
				<DeskInput v-model="toFilter" type="date" class="!w-36" />
			</template>

			<template #cell-name="{ row }">
				<div class="font-mono text-xs text-brand-700">{{ row.name }}</div>
				<div v-if="row.customer_type" class="text-[10px] text-ink-500">
					{{ row.customer_type }}
				</div>
			</template>

			<template #cell-valid_till="{ row }">
				<span v-if="!row.valid_till" class="text-ink-400">—</span>
				<span v-else :class="isLapsed(row) ? 'text-warning-700 font-medium' : ''">
					{{ fmtDate(row.valid_till) }}
				</span>
			</template>

			<template #cell-title="{ row }">
				<span class="text-ink-900 font-medium">{{ row.title || "—" }}</span>
			</template>

			<template #cell-grand_total="{ row }">
				<span class="text-xs tabular-nums text-ink-900 font-medium">
					{{ fmtCurrency(row.grand_total, row.currency) }}
				</span>
			</template>

			<template #cell-status="{ row }">
				<StatusBadge :status="statusLabel(row.status)" size="xs" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
