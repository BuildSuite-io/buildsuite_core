<script setup>
// Tenders — formal bids against published invitations. Page shell; the list, filters and
// cards land once the doctype carries status and totals.

import { ref, computed } from "vue";
import { RouterLink } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { fmtDate } from "@/utils/format";

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

const columns = [
	{ key: "name", label: "Tender" },
	{ key: "title", label: "For" },
	{ key: "issuing_body", label: "Issuing body" },
	{ key: "submission_deadline", label: "Deadline" },
	{ key: "emd_amount", label: "EMD", align: "right" },
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
			empty-message="No tenders yet.">
			<template #filter-chips>
				<DeskSelect v-model="envelopeFilter" class="!w-44">
					<option value="">Envelope: Any</option>
					<option>Single</option>
					<option>Two-envelope</option>
					<option>Three-envelope</option>
				</DeskSelect>

				<DeskInput v-model="fromFilter" type="date" class="!w-36" />
				<DeskInput v-model="toFilter" type="date" class="!w-36" />
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
