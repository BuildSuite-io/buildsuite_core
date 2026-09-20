<script setup>
// Quotations — priced offers to customers, on ERPNext's own Quotation doctype.
// Drafts only for now: nothing here submits, so there is no status to show or filter on.

import { ref, computed } from "vue";
import { useRouter, RouterLink } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useCustomerOptions } from "@/composables/useCustomerOptions";
import { fmtCurrency, fmtDate } from "@/utils/format";

const router = useRouter();
const { customerOptions } = useCustomerOptions();

function openQuotation(row) {
	router.push(`/quotations/${encodeURIComponent(row.name)}`);
}

const customerFilter = ref("");
const customerTypeFilter = ref("");
const fromFilter = ref("");
const toFilter = ref("");

const filterValues = computed(() => ({
	customer: customerFilter.value,
	customer_type: customerTypeFilter.value,
	from: fromFilter.value,
	to: toFilter.value,
}));

// A quotation past its validity date is not wrong, but it is no longer an offer — worth
// spotting in the column before someone quotes it back at you.
const TODAY = new Date().toISOString().slice(0, 10);

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Estimation", to: "/estimation" },
	{ label: "Quotations" },
];

// Passing `columns` makes DocTypeListView derive the query from them and ignore `field-order`
// entirely, so any field a cell template reads has to be named on its own column.
const columns = [
	{ key: "name", label: "Quotation", fields: ["name", "customer_type"] },
	{ key: "title", label: "For" },
	{ key: "party_name", label: "Customer" },
	{ key: "transaction_date", label: "Issued" },
	{ key: "valid_till", label: "Valid to" },
	{ key: "grand_total", label: "Value", align: "right", fields: ["grand_total", "currency"] },
];
</script>

<template>
	<DeskPage title="Quotations"
		subtitle="Priced offers to customers who asked you for a price. Nothing here touches an estimate — a price you offer is not work you have committed to."
		:breadcrumbs="breadcrumbs" printable>
		<template #actions>
			<RouterLink to="/quotations/new" class="desk-save-btn !text-xs">+ New</RouterLink>
		</template>

		<DocTypeListView doctype="Quotation" :columns="columns" :filter-values="filterValues"
			:filter-field-map="{
				customer: 'party_name',
				customer_type: 'customer_type',
				from: { field: 'transaction_date', op: '>=' },
				to: { field: 'transaction_date', op: '<=' },
			}" :search-fields="['name', 'party_name', 'title']" cache-key="buildsuite-quotation-list" row-key="name"
			search-placeholder="Search quotation / customer / scope…"
			empty-message="No quotations yet. Build one when a customer asks you for a price."
			@row-click="openQuotation">
			<template #filter-chips>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Customer</span>
					<DeskSearchableSelect v-model="customerFilter" :options="customerOptions" allow-clear
						placeholder="Any" search-placeholder="Search customers…" class="!w-52" />
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Type</span>
					<DeskSelect v-model="customerTypeFilter" class="!w-40">
						<option value="">Any</option>
						<option>Homebuyer</option>
						<option>Private Client</option>
						<option>Main Contractor</option>
					</DeskSelect>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Issued</span>
					<DeskInput v-model="fromFilter" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">to</span>
					<DeskInput v-model="toFilter" type="date" class="!w-36" />
				</label>
			</template>

			<template #cell-name="{ row }">
				<div class="font-mono text-xs text-brand-700">{{ row.name }}</div>
				<div v-if="row.customer_type" class="text-[10px] text-ink-500">
					{{ row.customer_type }}
				</div>
			</template>

			<template #cell-title="{ row }">
				<span class="text-ink-900 font-medium">{{ row.title || "—" }}</span>
			</template>

			<template #cell-valid_till="{ row }">
				<span v-if="!row.valid_till" class="text-ink-400">—</span>
				<span v-else :class="row.valid_till < TODAY ? 'text-warning-700 font-medium' : ''">
					{{ fmtDate(row.valid_till) }}
				</span>
			</template>

			<template #cell-grand_total="{ row }">
				<span class="text-xs tabular-nums text-ink-900 font-medium">
					{{ fmtCurrency(row.grand_total, row.currency) }}
				</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
