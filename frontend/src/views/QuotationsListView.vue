<script setup>
// Quotations — priced offers to a customer who asked us for a price.
//
// Backed by ERPNext's Quotation, so submit/cancel/amend, taxes, terms, print and
// the daily set_expired_status job all come for free.

import { computed, onMounted, ref } from "vue";
import { fmtINR, fmtCompactINR, fmtDate } from "@/utils/format";
import { getDeskUrl } from "@/utils/session";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { getQuotationSummary } from "@/data/quotationApi";

// A paged list resource cannot SUM across the whole set, so the cards come from
// their own endpoint. Loaded once — they do not track the list's filters.
const summary = ref(null);
const summaryError = ref("");

onMounted(async () => {
	try {
		summary.value = await getQuotationSummary();
	} catch (err) {
		summaryError.value = err.message;
	}
});

const cards = computed(() => {
	const s = summary.value;
	const nothingDecided = s && s.win_rate === null;
	return [
		{
			label: "Out with customers",
			value: s ? fmtCompactINR(s.pipeline_value) : "—",
			sub: "sent, no answer yet",
			tone: "text-ink-900",
		},
		{
			label: "Won",
			value: s ? fmtCompactINR(s.won_value) : "—",
			sub: "accepted by the customer",
			tone: "text-success-700",
		},
		{
			label: "Win rate",
			value: s && s.win_rate !== null ? `${s.win_rate}%` : "—",
			sub: nothingDecided ? "nothing decided yet" : "of quotations actually decided",
			tone: "text-ink-900",
		},
		{
			label: "Past their validity",
			value: s ? String(s.lapsed_count) : "—",
			sub: "chase, or let them go",
			tone: s && s.lapsed_count ? "text-warning-700" : "text-ink-900",
		},
	];
});

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Estimation", to: "/estimation" },
	{ label: "Quotations" },
];

// ERPNext's selling vocabulary -> what a construction estimator calls it.
// Display only; stored values never change.
const STATUS_LABELS = {
	Open: "Sent",
	Ordered: "Accepted",
	"Partially Ordered": "Partially accepted",
	Lost: "Rejected",
};
const statusLabel = (s) => STATUS_LABELS[s] || s || "—";

// ERPNext's Quotation statuses, in workflow order.
const STATUSES = [
	"Draft",
	"Open",
	"Replied",
	"Partially Ordered",
	"Ordered",
	"Lost",
	"Expired",
	"Cancelled",
];

const FIELDS = [
	"name",
	"title",
	"customer_name",
	"party_name",
	"custom_counterparty_type",
	"transaction_date",
	"valid_till",
	"grand_total",
	"status",
];

const columns = [
	{ key: "name", label: "Quotation" },
	{ key: "title", label: "For" },
	{ key: "customer_name", label: "Customer" },
	{ key: "transaction_date", label: "Issued" },
	{ key: "valid_till", label: "Valid to" },
	{ key: "grand_total", label: "Value", align: "right" },
	{ key: "status", label: "Status" },
];

// A date range needs two entries on one field, which the filter spec allows via
// an explicit operator.
const customerFilter = ref("");
const typeFilter = ref("");
const statusFilter = ref("");
const issuedFrom = ref("");
const issuedTo = ref("");

const filterValues = computed(() => ({
	customer: customerFilter.value,
	counterpartyType: typeFilter.value,
	status: statusFilter.value,
	issuedFrom: issuedFrom.value,
	issuedTo: issuedTo.value,
}));

// DocTypeListView's own Clear only covers its `+ Add filter` chips, so these
// need their own — a set date range otherwise has no indicator and no way back.
const anyFilter = computed(
	() =>
		!!(
			customerFilter.value ||
			typeFilter.value ||
			statusFilter.value ||
			issuedFrom.value ||
			issuedTo.value
		)
);

function clearAllFilters() {
	customerFilter.value = "";
	typeFilter.value = "";
	statusFilter.value = "";
	issuedFrom.value = "";
	issuedTo.value = "";
}

const filterFieldMap = {
	customer: "party_name",
	counterpartyType: "custom_counterparty_type",
	status: "status",
	issuedFrom: { field: "transaction_date", op: ">=" },
	issuedTo: { field: "transaction_date", op: "<=" },
};

// Local date parts, NOT toISOString(): that converts to UTC first, so in IST it
// returns yesterday for the first 5.5 hours of every day. Same trap the store's
// todayISO() helper exists to avoid.
const today = (() => {
	const d = new Date();
	const p = (n) => String(n).padStart(2, "0");
	return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
})();

// A quotation still out with the customer, past the date it was good until.
function lapsed(row) {
	return row.status === "Open" && row.valid_till && row.valid_till < today;
}

// No detail or create view yet, so both point at Desk.
const deskUrl = getDeskUrl();
const newQuotationUrl = `${deskUrl}/quotation/new`;

function onRowClick(row) {
	window.open(`${deskUrl}/quotation/${encodeURIComponent(row.name)}`, "_blank");
}
</script>

<template>
	<DeskPage
		title="Quotations"
		subtitle="Priced offers to customers who asked you for a price. Nothing here touches an estimate — a price you offer is not work you have committed to."
		:breadcrumbs="breadcrumbs"
		printable
	>
		<template #actions>
			<a :href="newQuotationUrl" target="_blank" rel="noopener" class="desk-save-btn"
				>+ New</a
			>
		</template>

		<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
			<div
				v-for="card in cards"
				:key="card.label"
				class="bg-white border border-ink-200 px-3 py-2"
				style="border-radius: 6px"
			>
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ card.label }}
				</div>
				<div class="text-base font-semibold tabular-nums" :class="card.tone">
					{{ card.value }}
				</div>
				<div class="text-[10px] text-ink-500">{{ card.sub }}</div>
			</div>
		</div>

		<div v-if="summaryError" class="text-[11px] text-danger-700 mb-3">
			{{ summaryError }}
		</div>

		<DocTypeListView
			doctype="Quotation"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'title', 'customer_name', 'party_name']"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			initial-order-by="transaction_date desc"
			cache-key="buildsuite-quotation-list"
			row-key="name"
			search-placeholder="Search quotation / customer / scope…"
			empty-message="No quotations yet. Build one when a customer asks you for a price."
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<DeskLinkPicker
					v-if="!customerFilter"
					v-model="customerFilter"
					doctype="Customer"
					label-field="name"
					value-field="name"
					placeholder="All customers"
					class="!w-52"
				/>
				<DeskFilterChip
					v-else
					label="Customer"
					:value="customerFilter"
					@remove="customerFilter = ''"
				/>

				<DeskSelect v-if="!typeFilter" v-model="typeFilter" class="!w-40">
					<option value="">Customer type: Any</option>
					<option value="Homebuyer">Homebuyer</option>
					<option value="Private Client">Private Client</option>
					<option value="Main Contractor">Main Contractor</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Customer type"
					:value="typeFilter"
					@remove="typeFilter = ''"
				/>

				<DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-36">
					<option value="">Status: Any</option>
					<option v-for="s in STATUSES" :key="s" :value="s">
						{{ statusLabel(s) }}
					</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Status"
					:value="statusLabel(statusFilter)"
					@remove="statusFilter = ''"
				/>

				<DeskInput v-model="issuedFrom" type="date" class="!w-36" title="Issued from" />
				<span class="text-[11px] text-ink-400">to</span>
				<DeskInput v-model="issuedTo" type="date" class="!w-36" title="Issued to" />

				<button
					v-if="anyFilter"
					type="button"
					class="text-[11px] text-brand-700 hover:underline"
					@click="clearAllFilters"
				>
					Clear filters
				</button>
			</template>

			<template #cell-name="{ row }">
				<!-- Not a RouterLink: /quotations/:id does not exist yet. -->
				<DeskLink
					:href="`${deskUrl}/quotation/${encodeURIComponent(row.name)}`"
					target="_blank"
					class="font-mono text-xs"
					@click.stop
					>{{ row.name }}</DeskLink
				>
				<div v-if="row.custom_counterparty_type" class="text-[10px] text-ink-500">
					{{ row.custom_counterparty_type }}
				</div>
			</template>

			<template #cell-title="{ row }">
				<span class="text-ink-900 font-medium">{{ row.title || "—" }}</span>
			</template>

			<template #cell-customer_name="{ row }">
				<span class="text-ink-700">{{ row.customer_name || row.party_name || "—" }}</span>
			</template>

			<template #cell-transaction_date="{ row }">
				<span class="text-ink-700 text-xs">{{ fmtDate(row.transaction_date) }}</span>
			</template>

			<template #cell-valid_till="{ row }">
				<span v-if="!row.valid_till" class="text-ink-300">—</span>
				<span
					v-else
					class="text-xs"
					:class="lapsed(row) ? 'text-warning-700 font-medium' : 'text-ink-700'"
					:title="lapsed(row) ? 'Past its validity — chase it, or let it go' : null"
					>{{ fmtDate(row.valid_till) }}</span
				>
			</template>

			<template #cell-grand_total="{ row }">
				<span class="text-sm font-medium text-ink-900 tabular-nums">{{
					fmtINR(row.grand_total)
				}}</span>
			</template>

			<template #cell-status="{ row }">
				<StatusBadge :status="statusLabel(row.status)" size="xs" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
