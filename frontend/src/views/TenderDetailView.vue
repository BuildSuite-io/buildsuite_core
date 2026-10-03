<script setup>
// Tender detail — header, summary cards, items and actions.

import { computed } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { parseFrappeError } from "@/utils/frappeError";
import { fmtCurrency, fmtDate } from "@/utils/format";
import { toDateInputValue } from "@/utils/dateInput";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import TenderSections from "@/components/TenderSections.vue";

const props = defineProps({ id: { type: String, required: true } });

const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const resource = adapter.read("BuildSuite Tenders", props.id);
const doc = computed(() => resource?.doc || null);
// `doc` is null while the fetch is in flight too, so the empty state has to wait for it.
const loading = computed(() => !!(resource?.loading ?? resource?.get?.loading));

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Estimation"), to: "/estimation" },
	{ label: __("Tenders"), to: "/tenders" },
	{ label: doc.value?.title || props.id },
]);

const subtitle = computed(() =>
	[props.id, doc.value?.issuing_body, doc.value?.tender_reference].filter(Boolean).join(" · ")
);

// The totals are stored on the tender, set by calculate_items() on every save — read them
// rather than re-deriving them here, so the page and the list can never disagree.
const rows = computed(() => doc.value?.buildsuite_tenders_items || []);
const taxable = computed(() => Number(doc.value?.bid_before_tax) || 0);
const total = computed(() => Number(doc.value?.bid_value) || 0);
const cost = computed(() => Number(doc.value?.subtotal) || 0);
const margin = computed(() => Number(doc.value?.margin_amount) || 0);
const tax = computed(() => Number(doc.value?.tax_amount) || 0);
const pbg = computed(() => Number(doc.value?.performance_guarantee_percent) || 0);

const TODAY = toDateInputValue(new Date());
const deadlineGone = computed(
	() => !!doc.value?.submission_deadline && doc.value.submission_deadline < TODAY
);

// Saved as each change is made — there is no Save button on this page.
async function persistSections(field, rows) {
	try {
		await adapter.update("BuildSuite Tenders", props.id, { [field]: rows });
		await resource?.reload?.();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? __("Failed to update sections"), "error");
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: __("Delete tender"),
		message: __('Delete "{0}"? This cannot be undone.', [doc.value?.title || props.id]),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("BuildSuite Tenders", props.id);
		router.push("/tenders");
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? __("Failed to delete tender"), "error");
	}
}
</script>

<template>
	<div v-if="!doc" class="px-6 py-12 text-center text-ink-500">
		<div v-if="loading" class="text-sm">{{ __("Loading tender…") }}</div>
		<template v-else>
			<div class="text-sm">Tender <span class="font-mono">{{ id }}</span> not found.</div>
			<DeskLink to="/tenders" class="text-sm mt-2 inline-block">{{ __("← Back to tenders") }}</DeskLink>
		</template>
	</div>

	<DeskPage v-else :title="doc?.title || id" :subtitle="subtitle" :breadcrumbs="breadcrumbs"
		printable>
		<template #actions>
			<RouterLink :to="`/tenders/${id}/edit`"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px">
				{{ __("Edit") }}
			</RouterLink>
			<button type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px" @click="onDelete">
				{{ __("Delete") }}
			</button>
		</template>

		<div v-if="deadlineGone" class="bg-danger-50 border border-danger-200 px-3 py-2.5 mb-3"
			style="border-radius: 2px">
			<div class="text-xs text-ink-900 font-medium">
				{{ __("The submission deadline passed on {0}.", [fmtDate(doc.submission_deadline)]) }}
			</div>
			<div class="text-[11px] text-ink-600">
				{{ __("Unlike a quotation past its validity, this cannot be chased — the bid can no longer be entered.") }}
			</div>
		</div>

		<div class="grid grid-cols-2 md:grid-cols-6 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">{{ __("Deadline") }}</div>
				<div class="text-sm font-medium mt-0.5"
					:class="deadlineGone ? 'text-danger-700' : 'text-ink-900'">
					{{ doc?.submission_deadline ? fmtDate(doc.submission_deadline) : "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">{{ __("Envelope") }}</div>
				<div class="text-sm font-medium text-ink-900 mt-0.5">
					{{ doc?.envelope_structure ? __(doc.envelope_structure) : "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Earnest money") }}
				</div>
				<div class="text-sm font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ doc?.emd_amount ? fmtCurrency(doc.emd_amount) : "—" }}
				</div>
				<div v-if="doc?.emd_instrument" class="text-[10px] text-ink-500 truncate"
					:title="doc.emd_instrument">
					{{ doc.emd_instrument }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Performance guarantee") }}
				</div>
				<div class="text-sm font-medium text-ink-900 tabular-nums mt-0.5">
					{{ pbg ? `${pbg}%` : "—" }}
				</div>
				<div v-if="pbg" class="text-[10px] text-ink-500">
					{{ __("{0} on award", [fmtCurrency((taxable * pbg) / 100)]) }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">{{ __("Bid value") }}</div>
				<div class="text-sm font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ fmtCurrency(total) }}
				</div>
				<div class="text-[10px] text-ink-500">{{ __("incl. tax") }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Prepared by") }}
				</div>
				<div class="flex items-center gap-1.5 mt-0.5">
					<UserAvatar v-if="doc?.owner" :user-id="doc.owner" size="xs" />
					<span class="text-sm text-ink-900 truncate">{{ doc?.owner || "—" }}</span>
				</div>
			</div>
		</div>

		<div v-if="doc?.portal || doc?.emd_valid_until || doc?.project"
			class="text-xs text-ink-600 mb-4 flex flex-wrap items-center gap-x-4 gap-y-1">
			<span v-if="doc.portal">{{ __("Portal:") }} <span class="text-ink-900">{{ doc.portal }}</span></span>
			<span v-if="doc.emd_valid_until">
				{{ __("EMD valid to") }} <span class="text-ink-900">{{ fmtDate(doc.emd_valid_until) }}</span>
			</span>
			<span v-if="doc.project">
				{{ __("Project:") }} <DeskLink :to="`/projects/${doc.project}`">{{ doc.project }}</DeskLink>
			</span>
		</div>

		<TenderSections :sections="doc?.preamble_sections || []" editable :title="__('Before the items')"
			class="mb-4" :empty-hint="__('Nothing ahead of the item table.')"
			:purpose-hint="__('Optional — scope of work, preamble or method of measurement, printed above the priced schedule.')"
			@update:sections="(v) => persistSections('preamble_sections', v)" />

		<div class="text-xs text-ink-500 mb-2">
			{{ rows.length === 1 ? __("{0} line", [rows.length]) : __("{0} lines", [rows.length]) }}
		</div>

		<div class="border border-ink-200 overflow-x-auto" style="border-radius: 2px">
			<table class="w-full text-xs" style="min-width: 720px">
				<thead class="bg-ink-50 text-[10px] uppercase tracking-wider text-ink-500">
					<tr>
						<th class="text-left font-medium px-3 py-2.5 w-24">{{ __("Source") }}</th>
						<th class="text-left font-medium px-3 py-2.5">{{ __("Description") }}</th>
						<th class="text-left font-medium px-3 py-2.5 w-20">{{ __("Unit") }}</th>
						<th class="text-right font-medium px-3 py-2.5 w-20">{{ __("Qty") }}</th>
						<th class="text-right font-medium px-3 py-2.5 w-28">{{ __("Rate") }}</th>
						<th class="text-right font-medium px-3 py-2.5 w-28">
							{{ __("Sell rate") }}
							<div class="normal-case tracking-normal text-ink-400 font-normal">
								{{ __("+{0}% margin", [Number(doc?.margin_percent) || 0]) }}
							</div>
						</th>
						<th class="text-right font-medium px-3 py-2.5 w-32">{{ __("Amount") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr v-if="!rows.length">
						<td colspan="7" class="px-3 py-8 text-center text-ink-400">
							{{ __("No items on this tender.") }}
						</td>
					</tr>
					<tr v-for="r in rows" :key="r.name" class="border-t border-ink-100 align-top">
						<td class="px-3 py-3">
							<StatusBadge v-if="r.source" :status="r.source" size="xs" />
						</td>
						<td class="px-3 py-3 text-sm text-ink-900">
							{{ r.description }}
							<div v-if="r.source_ref" class="text-[10px] text-ink-500 font-mono">
								{{ r.source_ref }}
							</div>
						</td>
						<td class="px-3 py-3 text-ink-600">{{ r.unit || "—" }}</td>
						<td class="px-3 py-3 text-right tabular-nums">{{ r.qty }}</td>
						<td class="px-3 py-3 text-right tabular-nums">{{ fmtCurrency(r.rate) }}</td>
						<td class="px-3 py-3 text-right tabular-nums">{{ fmtCurrency(r.sell_rate) }}</td>
						<td class="px-3 py-3 text-right tabular-nums font-medium text-ink-900">
							{{ fmtCurrency(r.amount) }}
							<div class="text-[10px] text-ink-400 font-normal">
								{{ __("cost {0}", [fmtCurrency((Number(r.qty) || 0) * (Number(r.rate) || 0))]) }}
							</div>
						</td>
					</tr>
				</tbody>
				<tfoot v-if="rows.length" class="bg-ink-50 border-t border-ink-200">
					<tr>
						<td colspan="6"
							class="px-3 pt-3 text-right text-[10px] uppercase tracking-wider text-ink-600 font-medium">
							{{ __("Price before tax") }}
						</td>
						<td class="px-3 pt-3 text-right text-sm font-semibold text-ink-900 tabular-nums">
							{{ fmtCurrency(taxable) }}
						</td>
					</tr>
					<tr>
						<td colspan="7"
							class="px-3 pb-3 pt-1 text-right text-[10px] uppercase tracking-wider text-ink-500">
							{{ __("of which cost {0} · margin {1}", [fmtCurrency(cost), fmtCurrency(margin)]) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
			<TenderSections :sections="doc?.terms_sections || []" editable class="lg:col-span-2"
				:title="__('Terms & conditions')" :empty-hint="__('No terms sections yet.')"
				:purpose-hint="__('A tender usually carries several — general conditions, payment, eligibility, defect liability.')"
				@update:sections="(v) => persistSections('terms_sections', v)" />

			<div class="border border-ink-200 bg-white self-start" style="border-radius: 2px">
				<div class="px-3 py-2 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Pricing") }}
				</div>
				<dl class="px-3 py-2 text-xs">
					<div class="flex justify-between py-1">
						<dt class="text-ink-600">{{ __("Subtotal") }}</dt>
						<dd class="tabular-nums text-ink-900">{{ fmtCurrency(cost) }}</dd>
					</div>
					<div class="flex justify-between py-1">
						<dt class="text-ink-600">{{ __("Margin {0}%", [Number(doc?.margin_percent) || 0]) }}</dt>
						<dd class="tabular-nums text-ink-900">{{ fmtCurrency(margin) }}</dd>
					</div>
					<div class="flex justify-between py-1 border-t border-ink-100 mt-1 pt-2">
						<dt class="text-ink-600">{{ __("Bid before tax") }}</dt>
						<dd class="tabular-nums text-ink-900">{{ fmtCurrency(taxable) }}</dd>
					</div>
					<div class="flex justify-between py-1">
						<dt class="text-ink-600">{{ __("Tax {0}%", [Number(doc?.tax_percent) || 0]) }}</dt>
						<dd class="tabular-nums text-ink-900">{{ fmtCurrency(tax) }}</dd>
					</div>
					<div class="flex justify-between border-t border-ink-200 mt-1 pt-2 font-semibold">
						<dt class="text-ink-900">{{ __("Total") }}</dt>
						<dd class="tabular-nums text-ink-900">{{ fmtCurrency(total) }}</dd>
					</div>
				</dl>
			</div>
		</div>
		<div v-if="doc.notes" class="mt-4 bg-ink-50 border border-ink-200 px-4 py-3"
			style="border-radius: 2px">
			<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">
				{{ __("Internal note — not printed") }}
			</div>
			<p class="text-sm text-ink-700 whitespace-pre-line">{{ doc.notes }}</p>
		</div>
	</DeskPage>
</template>
