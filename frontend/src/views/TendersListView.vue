<script setup>
// Tenders — formal bids against published invitations.
//
// The list leads with the deadline, not the value: a quotation past its validity can be chased,
// a tender past its deadline cannot be entered at all. The figures above the list come from
// api.tender.tender_kpis (over the tenders the user can read).

import { ref, computed, onMounted } from "vue";
import { RouterLink, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { TENDER_STATUSES, getTenderKpis } from "@/data/tenderApi";
import { fmtCompactCurrency, fmtCurrency, fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Sales"), to: "/sales" },
	{ label: __("Tenders") },
];

const FIELDS = ["name", "title", "issuing_body", "submission_deadline", "emd_amount", "status"];

const { selectOptions } = useDoctypeMeta("BuildSuite Tenders");
const envelopeOptions = computed(() => selectOptions("envelope_structure"));

const envelopeFilter = ref("");
const statusFilter = ref("");
const fromFilter = ref("");
const toFilter = ref("");

// The keys here are ours; filter-field-map below says which doctype field each one targets.
// A blank value switches its filter off.
const filterValues = computed(() => ({
	envelope: envelopeFilter.value,
	status: statusFilter.value,
	from: fromFilter.value,
	to: toFilter.value,
}));

// The figures above the list. A failure leaves them out rather than showing zeros.
const kpis = ref(null);
onMounted(async () => {
	try {
		kpis.value = await getTenderKpis();
	} catch {
		kpis.value = null;
	}
});
const dueSoon = computed(() => kpis.value?.due_soon || []);

const TODAY = new Date().toISOString().slice(0, 10);

// `fields` is what the row actually fetches. Passing `columns` makes DocTypeListView ignore
// `field-order` entirely (it derives the query from the columns), so the sub-lines below have
// to name the extra fields they read or they render blank.
const columns = [
	{ key: "name", label: __("Tender"), fields: ["name", "tender_reference", "issued_by"] },
	{
		key: "title",
		label: __("For"),
		fields: ["title", "envelope_structure", "items_count", "margin_percent"],
	},
	{ key: "issuing_body", label: __("Issuing body") },
	{
		key: "submission_deadline",
		label: __("Deadline"),
		fields: ["submission_deadline", "status"],
	},
	{ key: "emd_amount", label: __("EMD"), align: "right" },
	{ key: "bid_value", label: __("Bid value"), align: "right" },
	{ key: "status", label: __("Status") },
];
</script>

<template>
	<DeskPage
		:title="__('Tenders')"
		:subtitle="
			__(
				'Formal bids against published invitations. Nothing here touches an estimate — a bid you lose must cost the estimate nothing.'
			)
		"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<RouterLink to="/tenders/new" class="desk-save-btn !text-xs">{{
				__("+ New")
			}}</RouterLink>
		</template>

		<!-- Deadlines lead. Miss one and the bid cannot be entered at all, so it is surfaced
		     BEFORE the date rather than reported after it. -->
		<div
			v-if="dueSoon.length"
			class="bg-warning-50 border border-warning-200 px-3 py-2.5 mb-3"
			style="border-radius: 6px"
		>
			<div class="text-[10px] uppercase tracking-wider text-ink-600 font-medium mb-1">
				{{ __("Deadlines inside a week") }}
			</div>
			<RouterLink
				v-for="t in dueSoon"
				:key="t.name"
				:to="`/tenders/${t.name}`"
				class="flex items-center gap-2 py-0.5 text-xs hover:underline"
			>
				<span
					class="font-medium shrink-0"
					:class="t.overdue ? 'text-danger-700' : 'text-ink-900'"
				>
					{{
						t.overdue
							? __("Missed {0}", [fmtDate(t.submission_deadline)])
							: __("Due {0}", [fmtDate(t.submission_deadline)])
					}}
				</span>
				<span class="text-ink-700 truncate">{{ t.title }}</span>
			</RouterLink>
		</div>

		<div v-if="kpis" class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("In play") }}
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums">
					{{ kpis.in_play }}
				</div>
				<div class="text-[10px] text-ink-500">
					{{ __("preparing, submitted or being evaluated") }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Earnest money at stake") }}
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums">
					{{ fmtCompactCurrency(kpis.emd_at_stake) }}
				</div>
				<div class="text-[10px] text-ink-500">
					{{ __("lodged on bids not yet decided") }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Awarded") }}
				</div>
				<div class="text-base font-semibold text-success-700 tabular-nums">
					{{ fmtCompactCurrency(kpis.awarded_value) }}
				</div>
				<div class="text-[10px] text-ink-500">{{ __("value of bids we won") }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Win rate") }}
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums">
					{{ kpis.win_rate === null ? "—" : `${kpis.win_rate}%` }}
				</div>
				<div class="text-[10px] text-ink-500">
					{{
						kpis.win_rate === null
							? __("nothing decided yet")
							: __("of tenders actually decided")
					}}
				</div>
			</div>
		</div>

		<DocTypeListView
			doctype="BuildSuite Tenders"
			:field-order="FIELDS"
			:columns="columns"
			:filter-values="filterValues"
			:filter-field-map="{
				envelope: 'envelope_structure',
				status: 'status',
				from: { field: 'submission_deadline', op: '>=' },
				to: { field: 'submission_deadline', op: '<=' },
			}"
			:search-fields="['name', 'title', 'tender_reference', 'issuing_body']"
			cache-key="buildsuite-tender-list"
			row-key="name"
			:search-placeholder="__('Search tender / reference / issuing body')"
			:empty-message="__('No tenders yet. Start one when an invitation to bid comes in.')"
			@row-click="(row) => router.push(`/tenders/${row.name}`)"
		>
			<template #filter-chips>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Envelope")
					}}</span>
					<DeskSelect v-model="envelopeFilter" class="!w-40">
						<option value="">{{ __("Any") }}</option>
						<option v-for="o in envelopeOptions" :key="o" :value="o">
							{{ __(o) }}
						</option>
					</DeskSelect>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Status")
					}}</span>
					<DeskSelect v-model="statusFilter" class="!w-44">
						<option value="">{{ __("Any") }}</option>
						<option v-for="s in TENDER_STATUSES" :key="s" :value="s">
							{{ __(s) }}
						</option>
					</DeskSelect>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						__("Deadline")
					}}</span>
					<DeskInput v-model="fromFilter" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">{{ __("to") }}</span>
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
					{{ __(row.envelope_structure) }} · {{ row.items_count || 0 }}
					{{ row.items_count === 1 ? __("line") : __("lines") }} ·
					{{ __("{0}% margin", [row.margin_percent || 0]) }}
				</div>
			</template>

			<template #cell-emd_amount="{ row }">
				<span v-if="!row.emd_amount" class="text-ink-400">—</span>
				<span v-else class="tabular-nums text-ink-700">{{
					fmtCurrency(row.emd_amount)
				}}</span>
			</template>

			<template #cell-bid_value="{ row }">
				<span v-if="!row.bid_value" class="text-ink-400">—</span>
				<span v-else class="tabular-nums font-medium text-ink-900">
					{{ fmtCurrency(row.bid_value) }}
				</span>
			</template>

			<!-- Only a draft past its deadline is a problem: a submitted bid made it in time. -->
			<template #cell-submission_deadline="{ row }">
				<span v-if="!row.submission_deadline" class="text-ink-400">—</span>
				<span
					v-else
					:class="
						(row.status || 'Draft') === 'Draft' && row.submission_deadline < TODAY
							? 'text-danger-700 font-medium'
							: ''
					"
				>
					{{ fmtDate(row.submission_deadline) }}
				</span>
			</template>

			<template #cell-status="{ row }">
				<StatusBadge :status="row.status || 'Draft'" size="xs" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
