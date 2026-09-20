<script setup>
// Tenders — formal bids against published invitations.

import { ref, computed } from "vue";
import { RouterLink, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { fmtCurrency, fmtDate } from "@/utils/format";

const router = useRouter();

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Estimation", to: "/estimation" },
	{ label: "Tenders" },
];


const FIELDS = [
	"name",
	"title",
	"issuing_body",
	"submission_deadline",
	"emd_amount"
];

const { selectOptions } = useDoctypeMeta("BuildSuite Tenders");
const envelopeOptions = computed(() => selectOptions("envelope_structure"));

const envelopeFilter = ref("");
const fromFilter = ref("");
const toFilter = ref("");

// The keys here are ours; filter-field-map below says which doctype field each one targets.
// A blank value switches its filter off.
const filterValues = computed(() => ({
	envelope: envelopeFilter.value,
	from: fromFilter.value,
	to: toFilter.value,
}));




// A quotation past its validity can still be chased. A tender past its deadline cannot be
// entered at all, so the date is worth shouting about.
const TODAY = new Date().toISOString().slice(0, 10);

// `fields` is what the row actually fetches. Passing `columns` makes DocTypeListView ignore
// `field-order` entirely (it derives the query from the columns), so the sub-lines below have
// to name the extra fields they read or they render blank.
const columns = [
	{ key: "name", label: "Tender", fields: ["name", "tender_reference", "issued_by"] },
	{
		key: "title",
		label: "For",
		fields: ["title", "envelope_structure", "items_count", "margin_percent"],
	},
	{ key: "issuing_body", label: "Issuing body" },
	{ key: "submission_deadline", label: "Deadline" },
	{ key: "emd_amount", label: "EMD", align: "right" },
	{ key: "bid_value", label: "Bid value", align: "right" },
];

</script>

<template>
	<DeskPage title="Tenders"
		subtitle="Formal bids against published invitations. Nothing here touches an estimate — a bid you lose must cost the estimate nothing."
		:breadcrumbs="breadcrumbs" printable>
		<template #actions>
			<RouterLink to="/tenders/new" class="desk-save-btn !text-xs">+ New</RouterLink>
		</template>


		<DocTypeListView doctype="BuildSuite Tenders" :field-order="FIELDS" :columns="columns"
			:filter-values="filterValues"
			:filter-field-map="{
				envelope: 'envelope_structure',
				from: { field: 'submission_deadline', op: '>=' },
				to: { field: 'submission_deadline', op: '<=' },
			}"
			:search-fields="['name', 'title', 'tender_reference', 'issuing_body']" cache-key="buildsuite-tender-list"
			row-key="name" search-placeholder="Search tender / reference / issuing body"
			empty-message="No tenders yet. Start one when an invitation to bid comes in."
			@row-click="(row) => router.push(`/tenders/${row.name}`)">
			<template #filter-chips>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Envelope</span>
					<DeskSelect v-model="envelopeFilter" class="!w-40">
						<option value="">Any</option>
						<option v-for="o in envelopeOptions" :key="o" :value="o">{{ o }}</option>
					</DeskSelect>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Deadline</span>
					<DeskInput v-model="fromFilter" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">to</span>
					<DeskInput v-model="toFilter" type="date" class="!w-36" />
				</label>
			</template>

			<template #cell-name="{ row }">
				<DeskLink :to="`/tenders/${row.name}`" class="font-mono text-xs" @click.stop>
					{{ row.name }}
				</DeskLink>
				<div class="text-[10px] text-ink-500">
					{{ row.tender_reference || row.issued_by }}
				</div>
			</template>

			<template #cell-title="{ row }">
				<div class="text-ink-900 font-medium">{{ row.title }}</div>
				<div class="text-[10px] text-ink-500">
					{{ row.envelope_structure }} · {{ row.items_count || 0 }}
					line{{ row.items_count === 1 ? "" : "s" }} · {{ row.margin_percent || 0 }}% margin
				</div>
			</template>

			<template #cell-emd_amount="{ row }">
				<span v-if="!row.emd_amount" class="text-ink-400">—</span>
				<span v-else>{{ fmtCurrency(row.emd_amount) }}</span>
			</template>

			<template #cell-bid_value="{ row }">
				<span v-if="!row.bid_value" class="text-ink-400">—</span>
				<span v-else class="tabular-nums font-medium text-ink-900">
					{{ fmtCurrency(row.bid_value) }}
				</span>
			</template>

			<template #cell-submission_deadline="{ row }">
				<span v-if="!row.submission_deadline" class="text-ink-400">—</span>
				<span v-else :class="row.submission_deadline < TODAY ? 'text-danger-700 font-medium' : ''">
					{{ fmtDate(row.submission_deadline) }}
				</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
