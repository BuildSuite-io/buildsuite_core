<script setup>
// Quotations — priced offers to customers and leads, on ERPNext's own Quotation doctype.
// The status shown is the offer's (Draft / Sent / Accepted / Rejected / Expired / Cancelled),
// derived from ERPNext's fields in data/offerStatus.js; the status filter uses the same table.

import { ref, computed, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useCustomerOptions } from "@/composables/useCustomerOptions";
import StatusBadge from "@/components/StatusBadge.vue";
import { OFFER_STATUSES, OFFER_STATUS_FILTERS, offerStatus } from "@/data/offerStatus";
import { getQuotationKpis } from "@/data/quotationApi";
import { fmtCompactCurrency, fmtCurrency, fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();
const { customerOptions } = useCustomerOptions();

function openQuotation(row) {
	router.push(`/quotations/${encodeURIComponent(row.name)}`);
}

const customerFilter = ref("");
const customerTypeFilter = ref("");
const statusFilter = ref("");
// "Who it is with": a customer, or a lead that has not become one yet.
const toKindFilter = ref("");
const fromFilter = ref("");
const toFilter = ref("");

const baseFilters = computed(() => [
	...(OFFER_STATUS_FILTERS[statusFilter.value] || []),
	...(toKindFilter.value ? [["quotation_to", "=", toKindFilter.value]] : []),
]);

const filterValues = computed(() => ({
	customer: customerFilter.value,
	customer_type: customerTypeFilter.value,
	from: fromFilter.value,
	to: toFilter.value,
}));

// The figures above the list (api.quotation.quotation_kpis). A failure leaves them out rather
// than showing zeros.
const kpis = ref(null);
onMounted(async () => {
	try {
		kpis.value = await getQuotationKpis();
	} catch {
		kpis.value = null;
	}
});

// A quotation past its validity date is not wrong, but it is no longer an offer — worth
// spotting in the column before someone quotes it back at you.
const TODAY = new Date().toISOString().slice(0, 10);

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Sales"), to: "/sales" },
	{ label: __("Quotations") },
];

// Passing `columns` makes DocTypeListView derive the query from them and ignore `field-order`
// entirely, so any field a cell template reads has to be named on its own column.
const columns = [
	{ key: "name", label: __("Quotation"), fields: ["name", "customer_type"] },
	{ key: "title", label: __("Scope") },
	{
		key: "party_name",
		label: __("For"),
		fields: ["party_name", "customer_name", "quotation_to"],
	},
	{
		key: "offer_status",
		label: __("Status"),
		fields: ["docstatus", "status", "accepted_on"],
	},
	{ key: "transaction_date", label: __("Issued") },
	{ key: "valid_till", label: __("Valid to") },
	{
		key: "grand_total",
		label: __("Value"),
		align: "right",
		fields: ["grand_total", "currency"],
	},
];
</script>

<template>
	<DeskPage
		:title="__('Quotations')"
		:subtitle="
			__(
				'Priced offers to leads and customers who asked you for a price. Nothing here touches an estimate — a price you offer is not work you have committed to.'
			)
		"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<RouterLink to="/quotations/new" class="desk-save-btn !text-xs">{{
				__("+ New")
			}}</RouterLink>
		</template>

		<div v-if="kpis" class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Awaiting an answer") }}
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums">
					{{ fmtCompactCurrency(kpis.awaiting_value) }}
				</div>
				<div class="text-[10px] text-ink-500">{{ __("sent to leads and customers") }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Won") }}
				</div>
				<div class="text-base font-semibold text-success-700 tabular-nums">
					{{ fmtCompactCurrency(kpis.won_value) }}
				</div>
				<div class="text-[10px] text-ink-500">{{ __("accepted by the customer") }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Win rate") }}
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums">
					{{ kpis.win_rate === null ? "—" : `${kpis.win_rate}%` }}
				</div>
				<!-- Says what it counts: a win rate that quietly includes unanswered quotes measures
				     how much you send, not how much you win. -->
				<div class="text-[10px] text-ink-500">
					{{
						kpis.win_rate === null
							? __("nothing decided yet")
							: __("of quotations actually decided")
					}}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Past their validity") }}
				</div>
				<div
					class="text-base font-semibold tabular-nums"
					:class="kpis.past_validity ? 'text-warning-700' : 'text-ink-900'"
				>
					{{ kpis.past_validity }}
				</div>
				<div class="text-[10px] text-ink-500">{{ __("chase, or let them go") }}</div>
			</div>
		</div>

		<DocTypeListView
			doctype="Quotation"
			:columns="columns"
			:filter-values="filterValues"
			:base-filters="baseFilters"
			:filter-field-map="{
				customer: 'party_name',
				customer_type: 'customer_type',
				from: { field: 'transaction_date', op: '>=' },
				to: { field: 'transaction_date', op: '<=' },
			}"
			:search-fields="['name', 'party_name', 'customer_name', 'title']"
			cache-key="buildsuite-quotation-list"
			row-key="name"
			:search-placeholder="__('Search quotation / lead / customer / scope…')"
			:empty-message="
				__('No quotations yet. Build one when a customer asks you for a price.')
			"
			@row-click="openQuotation"
		>
			<template #filter-chips>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Customer")
					}}</span>
					<DeskSearchableSelect
						v-model="customerFilter"
						:options="customerOptions"
						allow-clear
						:placeholder="__('Any')"
						:search-placeholder="__('Search customers…')"
						class="!w-52"
					/>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Status")
					}}</span>
					<DeskSelect v-model="statusFilter" class="!w-32">
						<option value="">{{ __("Any") }}</option>
						<option v-for="s in OFFER_STATUSES" :key="s" :value="s">
							{{ __(s) }}
						</option>
					</DeskSelect>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Goes to")
					}}</span>
					<DeskSelect v-model="toKindFilter" class="!w-32">
						<option value="">{{ __("Any") }}</option>
						<option value="Customer">{{ __("Customer") }}</option>
						<option value="Lead">{{ __("Lead") }}</option>
					</DeskSelect>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Type")
					}}</span>
					<DeskSelect v-model="customerTypeFilter" class="!w-40">
						<option value="">{{ __("Any") }}</option>
						<option value="Homebuyer">{{ __("Homebuyer") }}</option>
						<option value="Private Client">{{ __("Private Client") }}</option>
						<option value="Main Contractor">{{ __("Main Contractor") }}</option>
					</DeskSelect>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Issued")
					}}</span>
					<DeskInput v-model="fromFilter" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">{{ __("to") }}</span>
					<DeskInput v-model="toFilter" type="date" class="!w-36" />
				</label>
			</template>

			<template #cell-name="{ row }">
				<div class="font-mono text-xs text-brand-700">{{ row.name }}</div>
				<div v-if="row.customer_type" class="text-[10px] text-ink-500">
					{{ __(row.customer_type) }}
				</div>
			</template>

			<template #cell-party_name="{ row }">
				<span class="text-ink-900">{{ row.customer_name || row.party_name || "—" }}</span>
				<span
					v-if="row.quotation_to === 'Lead'"
					class="ml-1.5 text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 bg-info-50 text-info-700"
					style="border-radius: 4px"
					>{{ __("Lead") }}</span
				>
			</template>

			<template #cell-offer_status="{ row }">
				<StatusBadge :status="offerStatus(row)" size="xs" />
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
